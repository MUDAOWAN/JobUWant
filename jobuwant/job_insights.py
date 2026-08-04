from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jobuwant.db import DB_PATH, connect


DEFAULT_OUTPUT = Path("data") / "boss_job_insights.json"


TAG_RULES: dict[str, dict[str, list[str]]] = {
    "programming_languages": {
        "C++": ["c++", "c/c++"],
        "Python": ["python"],
        "C": ["c语言", " c ", "c/"],
    },
    "slam_domains": {
        "SLAM": ["slam", "定位与建图"],
        "LiDAR SLAM": ["激光slam", "激光 slam", "lidar slam", "3d激光slam"],
        "Visual SLAM": ["视觉slam", "视觉 slam", "vslam", "visual slam"],
        "VIO": ["vio", "视觉惯性", "视觉-惯性"],
        "Localization": ["定位", "localization", "重定位"],
        "Mapping": ["建图", "mapping", "地图构建"],
        "Loop Closure": ["回环", "闭环", "loop closure"],
        "Navigation": ["导航", "navigation"],
        "Path Planning": ["路径规划", "path planning"],
        "Multi-Sensor Fusion": ["多传感器融合", "传感器融合", "sensor fusion"],
    },
    "sensors": {
        "LiDAR": ["lidar", "激光雷达"],
        'Camera': ['camera', '相机', 'rgbd', 'rgb-d', '双目', '单目'],
        "IMU": ["imu", "惯导", "惯性"],
        "Wheel Odometry": ["轮速计", "轮式里程计", "wheel odometry"],
        "RTK/GNSS": ["rtk", "gnss", "gps"],
        "Radar": ["毫米波雷达", "radar"],
    },
    "frameworks_tools": {
        "ROS": ["ros"],
        "ROS2": ["ros2"],
        "OpenCV": ["opencv"],
        "PCL": ["pcl", "point cloud library"],
        "Eigen": ["eigen"],
        "Ceres": ["ceres"],
        "g2o": ["g2o"],
        "GTSAM": ["gtsam"],
        "Linux": ["linux"],
        "Gazebo": ["gazebo"],
        "RViz": ["rviz"],
        "Open3D": ["open3d"],
    },
    "algorithms_math": {
        "Kalman Filter": ["kalman", "ekf", "eskf", "ukf", "卡尔曼"],
        "Graph Optimization": ["图优化", "graph optimization", "因子图"],
        "Bundle Adjustment": ["bundle adjustment", "ba优化"],
        "ICP/NDT": ["icp", "ndt", "gicp"],
        "Feature Extraction": ["特征提取", "orb", "sift", "surf", "superpoint"],
        "FAST-LIO": ["fast-lio"],
        "LIO-SAM": ["lio-sam"],
        "ORB-SLAM": ["orb-slam"],
        "VINS": ["vins"],
        "LOAM": ["loam"],
        "Linear Algebra": ["线性代数", "矩阵", "李群", "李代数"],
        "Optimization": ["优化", "非线性优化", "最小二乘"],
    },
    "ability_requirements": {
        "Math Foundation": ["数学基础", "线性代数", "概率统计", "几何", "李群", "李代数"],
        "Engineering Implementation": ["工程化", "落地", "部署", "移植", "产品化"],
        "Debugging And Testing": ["调试", "测试", "性能评估", "验证"],
        "System Design": ["架构设计", "系统设计", "方案设计"],
        "Research Tracking": ["前沿技术", "技术调研", "论文"],
        "Documentation": ["技术文档", "实验报告", "文档"],
        "Communication": ["沟通", "团队协作", "协作"],
    },
}


ROLE_FAMILY_RULES: dict[str, list[str]] = {
    "LiDAR SLAM": ["激光slam", "激光 slam", "lidar", "fast-lio", "lio-sam"],
    "Visual SLAM": ["视觉slam", "视觉 slam", "vslam", "rgbd", "orb-slam", "相机"],
    "Multi-Sensor Fusion": ["多传感器融合", "传感器融合", "imu", "rtk", "gnss"],
    "Robot Navigation": ["机器人", "导航", "路径规划", "运动规划"],
    "Perception/Image Processing": ["感知", "图像处理", "视觉识别"],
}


@dataclass(frozen=True)
class JobInsight:
    job_id: int
    company_name: str
    job_title: str
    city: str
    salary: str
    experience: str
    education: str
    role_families: list[str]
    tags: dict[str, list[str]]


def build_insights(conn: sqlite3.Connection, source_type: str = "boss") -> dict[str, Any]:
    rows = load_analysis_rows(conn, source_type)
    job_insights = [extract_job_insight(dict(row)) for row in rows]
    return {
        "source_type": source_type,
        "sample_count": len(job_insights),
        "jobs": [job.__dict__ for job in job_insights],
        "summary": summarize(job_insights),
    }


def load_analysis_rows(conn: sqlite3.Connection, source_type: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT
            id,
            company_name,
            job_title,
            city,
            raw_job_text,
            source_metadata_json
        FROM job_details
        WHERE source_type = ?
          AND quality_status = 'analysis_ready'
        ORDER BY id
        """,
        (source_type,),
    ).fetchall()


def extract_job_insight(row: dict[str, Any]) -> JobInsight:
    metadata = parse_metadata(row.get("source_metadata_json"))
    text = "\n".join(
        [
            text_value(row.get("job_title")),
            text_value(row.get("raw_job_text")),
        ]
    )
    tags = {
        group: match_labels(text, labels)
        for group, labels in TAG_RULES.items()
    }
    role_families = classify_role_families(text)
    return JobInsight(
        job_id=int(row["id"]),
        company_name=text_value(row.get("company_name")),
        job_title=text_value(row.get("job_title")),
        city=text_value(row.get("city")),
        salary=text_value(metadata.get("salary")),
        experience=text_value(metadata.get("experience")),
        education=text_value(metadata.get("education")),
        role_families=role_families,
        tags=tags,
    )


def summarize(jobs: list[JobInsight]) -> dict[str, Any]:
    return {
        "role_family_counts": count_items(job.role_families for job in jobs),
        "tag_counts": {
            group: count_items(getattr_job_tags(jobs, group))
            for group in TAG_RULES
        },
        "salary_counts": count_values(job.salary for job in jobs if job.salary),
        "experience_counts": count_values(job.experience for job in jobs if job.experience),
        "education_counts": count_values(job.education for job in jobs if job.education),
    }


def getattr_job_tags(jobs: list[JobInsight], group: str) -> list[list[str]]:
    return [job.tags.get(group, []) for job in jobs]


def count_items(items_by_job: list[list[str]]) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for items in items_by_job:
        counter.update(set(items))
    return [
        {"name": name, "job_count": count}
        for name, count in counter.most_common()
    ]


def count_values(values: object) -> list[dict[str, Any]]:
    counter = Counter(values)
    return [
        {"name": name, "job_count": count}
        for name, count in counter.most_common()
    ]


def match_labels(text: str, labels: dict[str, list[str]]) -> list[str]:
    lowered = normalize_text(text)
    matched: list[str] = []
    for label, terms in labels.items():
        if any(term.lower() in lowered for term in terms):
            matched.append(label)
    return matched


def classify_role_families(text: str) -> list[str]:
    matched = match_labels(text, ROLE_FAMILY_RULES)
    return matched or ["General SLAM"]


def normalize_text(text: str) -> str:
    return f" {text.lower()} "


def parse_metadata(value: object) -> dict[str, Any]:
    try:
        parsed = json.loads(text_value(value) or "{}")
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def text_value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def write_output(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build rule-based job insights from JobUWant SQLite.")
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--source-type", default="boss")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    conn = connect(args.db)
    payload = build_insights(conn, source_type=args.source_type)
    write_output(payload, args.output)
    print(
        json.dumps(
            {
                "source_type": payload["source_type"],
                "sample_count": payload["sample_count"],
                "output": str(args.output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
