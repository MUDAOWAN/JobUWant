from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from jobuwant.ai_job_extract import BatchExtractionOutput


def test_batch_extraction_allows_empty_graduate_friendliness_evidence() -> None:
    payload = {
        'jobs': [
            {
                'job_id': 1,
                'role_intent': 'intern',
                'normalized_role': 'AI 工程师实习生',
                'role_family': 'AI 工程',
                'technical_stack': [],
                'tools_platforms': [],
                'business_domains': [],
                'ability_requirements': [
                    {
                        'name': 'Python',
                        'category': 'language',
                        'importance': 'core',
                        'evidence': [
                            {'field': 'job_text', 'quote': '熟悉 Python', 'interpretation': '需要 Python 基础'}
                        ],
                    }
                ],
                'experience_requirements': {'level': '不限', 'summary': '', 'evidence': []},
                'education_requirements': {'level': '本科', 'summary': '', 'evidence': []},
                'graduate_friendliness': {'level': 'unclear', 'reason': '', 'evidence': []},
                'evidence': [],
            }
        ]
    }

    output = BatchExtractionOutput.model_validate(payload)

    assert output.jobs[0].graduate_friendliness.evidence == []
