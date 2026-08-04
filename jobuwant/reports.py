from __future__ import annotations

from html import escape

from jobuwant.models import DiscoveryResult


def render_html_report(result: DiscoveryResult) -> str:
    rows = "\n".join(
        "<tr>"
        f"<td>{escape(candidate.company_name)}</td>"
        f"<td>{escape(candidate.possible_category)}</td>"
        f"<td>{escape(candidate.related_direction)}</td>"
        f"<td>{escape(candidate.matched_keywords)}</td>"
        f"<td>{escape(candidate.confidence_label)}</td>"
        f"<td><a href=\"{escape(candidate.evidence_url)}\">\u6765\u6e90</a></td>"
        "</tr>"
        for candidate in result.candidates
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>JobUWant \u62a5\u544a</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2933; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 8px; text-align: left; }}
    th {{ background: #f0f4f8; }}
    .metric {{ display: inline-block; margin-right: 24px; }}
  </style>
</head>
<body>
  <h1>JobUWant \u62a5\u544a\u9884\u89c8</h1>
  <p>\u5f53\u524d\u9884\u89c8\u53ea\u4f7f\u7528\u672c\u5730\u6837\u4f8b\u6570\u636e\u3002</p>
  <section>
    <span class="metric">\u5019\u9009\u6765\u6e90\u6570\u91cf\uff1a{result.usage.candidate_sources}</span>
    <span class="metric">\u6a21\u578b\u8c03\u7528\u6b21\u6570\uff1a{result.usage.model_calls}</span>
    <span class="metric">\u9884\u4f30\u8d39\u7528\uff08\u5143\uff09\uff1a{result.usage.estimated_cny:.2f}</span>
  </section>
  <h2>\u5019\u9009\u516c\u53f8</h2>
  <table>
    <thead>
      <tr>
        <th>\u516c\u53f8</th>
        <th>\u7c7b\u522b</th>
        <th>\u76f8\u5173\u65b9\u5411</th>
        <th>\u5339\u914d\u5173\u952e\u8bcd</th>
        <th>\u7f6e\u4fe1\u5ea6</th>
        <th>\u8bc1\u636e</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>
"""
