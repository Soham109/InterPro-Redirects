import pandas as pd
import numpy as np
from urllib.parse import urlparse
from math import log2

def normalize(url):
    try:
        return urlparse(url).path.rstrip("/")
    except:
        return url

def entropy(values):
    probs = values.value_counts(normalize=True)
    return -sum(p * log2(p) for p in probs)

def analyze(csv="raw_404_logs.csv"):
    df = pd.read_csv(csv)

    df["normalized_url"] = df["source_url"].apply(normalize)
    df["is_php"] = df["normalized_url"].str.endswith(".php")
    df["ext"] = df["normalized_url"].str.extract(r"\.([a-zA-Z0-9]+)$")[0]

    ip_rows = []

    for ip, g in df.groupby("ip"):
        unique_urls = g["normalized_url"].nunique()
        php_hits = g["is_php"].sum()
        ent = entropy(g["normalized_url"])

        bot_score = (
            0.5 * unique_urls +
            1.5 * php_hits +
            2.0 * ent
        )

        ip_rows.append({
            "ip": ip,
            "total_hits": len(g),
            "unique_urls": unique_urls,
            "php_attempts": php_hits,
            "url_entropy": round(ent, 2),
            "bot_score": round(bot_score, 2),
            "suspected_bot": bot_score >= 10
        })

    ip_report = pd.DataFrame(ip_rows)

    # URL-level analysis (VERY IMPORTANT)
    url_report = (
        df.groupby("normalized_url")
          .agg(
              total_hits=("ip", "count"),
              unique_ips=("ip", "nunique"),
              php=("is_php", "sum")
          )
          .reset_index()
          .sort_values("total_hits", ascending=False)
    )

    ip_report.to_csv("404_ip_analysis.csv", index=False)
    url_report.to_csv("404_url_analysis.csv", index=False)

    return df, ip_report, url_report

if __name__ == "__main__":
    analyze()
