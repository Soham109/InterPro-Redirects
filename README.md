# InterPro 404 Redirects Analysis

A comprehensive toolkit for scraping, analyzing, and visualizing 404 errors from WordPress sites to intelligently distinguish between bot traffic and genuine user issues.

## 🎯 Project Overview

This project automates the process of:
1. **Scraping** 404 error logs from WordPress admin panels
2. **Analyzing** traffic patterns to identify bot vs. human behavior
3. **Visualizing** results through an interactive dashboard
4. **Generating** actionable redirect recommendations

## 📁 Project Structure

```
├── real_scraper.py          # Main scraper with Selenium
├── fast_scraper.py          # Alternative faster scraper
├── analyzer.py              # Bot detection & traffic analysis
├── dashboard.py             # Streamlit dashboard (optional)
├── requirements.txt         # Python dependencies
├── raw_404_logs.csv         # Scraped data (generated)
├── 404_ip_analysis.csv      # IP-level bot analysis (generated)
└── 404_url_analysis.csv     # URL-level traffic analysis (generated)
```

## 🚀 Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/Soham109/InterPro-Redirects.git
cd InterPro-Redirects

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Scraping 404 Logs

Run the scraper to collect data from WordPress:

```bash
python real_scraper.py
```

**What happens:**
- Opens Chrome browser
- Prompts you to log in to WordPress admin
- Navigates to the Redirection plugin's 404 logs
- Scrapes all pages automatically
- Saves data to `raw_404_logs.csv`

**Features:**
- Adaptive page loading (waits for full content)
- Handles pagination automatically
- Stops at empty pages
- Extracts: Date, Source URL, User Agent, IP Address

### 3. Analyze the Data

```bash
python analyzer.py
```

**Outputs:**
- `404_ip_analysis.csv` - Bot detection per IP
- `404_url_analysis.csv` - URL-level traffic summary

### 4. View Dashboard (Optional)

```bash
streamlit run dashboard.py
```

Access at `http://localhost:8501`

## 🧠 How Bot Detection Works

The analyzer uses a **heuristic scoring system** to identify bot traffic based on behavioral patterns.

### Bot Score Formula

```python
bot_score = (0.5 × unique_urls) + (1.5 × php_attempts) + (2.0 × url_entropy)
```

**If `bot_score ≥ 10` → Flagged as Bot**

### Scoring Factors

| Factor | Weight | Description |
|--------|--------|-------------|
| **Unique URLs** | 0.5 | Number of different URLs hit by this IP |
| **PHP Attempts** | 1.5 | Hits to `.php` files (common bot probes) |
| **URL Entropy** | 2.0 | Randomness/diversity of URL patterns |

### Understanding Entropy

**Entropy** measures how random or scattered an IP's requests are:

- **Low entropy (0-1)**: Focused traffic (e.g., human hitting same broken link)
- **High entropy (3+)**: Random probing across many URLs (typical bot behavior)

**Example Calculation:**

```
IP: 123.45.67.89
- Hits 8 unique URLs
- 4 are .php files  
- Entropy = 2.5

bot_score = (0.5 × 8) + (1.5 × 4) + (2.0 × 2.5)
          = 4.0 + 6.0 + 5.0
          = 15.0 → BOT ✅
```

### Why These Weights?

- **PHP files** are heavily weighted (1.5×) because legitimate sites rarely expose `.php` endpoints
- **Entropy** is the strongest signal (2.0×) - humans have predictable patterns, bots scatter
- **Unique URLs** provides baseline (0.5×) - even humans might hit a few broken links

## 📊 Output Files Explained

### 1. `raw_404_logs.csv`

Raw scraped data from WordPress:

| Column | Description |
|--------|-------------|
| `date` | Timestamp of 404 error |
| `source_url` | URL that was not found |
| `user_agent` | Browser/bot identifier |
| `ip` | IP address of requester |

### 2. `404_ip_analysis.csv`

Bot detection results per IP:

| Column | Description |
|--------|-------------|
| `ip` | IP address |
| `total_hits` | Total 404 requests from this IP |
| `unique_urls` | Number of different URLs accessed |
| `php_attempts` | Count of `.php` file requests |
| `url_entropy` | Randomness score (0-10+) |
| `bot_score` | Final calculated score |
| `suspected_bot` | `True` if bot_score ≥ 10 |

### 3. `404_url_analysis.csv`

Traffic summary per broken URL:

| Column | Description |
|--------|-------------|
| `normalized_url` | Cleaned URL path |
| `total_hits` | How many times this URL was requested |
| `unique_ips` | Number of different IPs hitting this URL |
| `php` | Whether this is a `.php` file |

## 🔍 Analysis Workflow

```
┌─────────────────┐
│  WordPress 404  │
│   Redirection   │
│      Logs       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  real_scraper   │  ← Selenium automation
│   .py scrapes   │
│   all pages     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ raw_404_logs    │
│     .csv        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   analyzer.py   │  ← Calculates bot scores
│   processes     │
│   patterns      │
└────────┬────────┘
         │
         ▼
┌─────────────────┬─────────────────┐
│ 404_ip_analysis │ 404_url_analysis│
│      .csv       │      .csv       │
│   (Bot Report)  │  (URL Summary)  │
└─────────────────┴─────────────────┘
         │
         ▼
┌─────────────────┐
│  dashboard.py   │  ← Streamlit UI
│  (Optional viz) │
└─────────────────┘
```

## 🛠️ Advanced Usage

### Customize Bot Detection Threshold

Edit `analyzer.py` line 44:

```python
"suspected_bot": bot_score >= 10  # Change 10 to your threshold
```

**Recommended thresholds:**
- `8` - More aggressive (catches more bots, some false positives)
- `10` - Balanced (default)
- `15` - Conservative (only obvious bots)

### Adjust Scoring Weights

Edit `analyzer.py` lines 31-35:

```python
bot_score = (
    0.5 * unique_urls +    # Increase to penalize URL diversity
    1.5 * php_hits +       # Increase to catch PHP probers
    2.0 * ent              # Most reliable signal
)
```

### Filter Analysis by Date Range

Modify `analyzer.py` after loading CSV:

```python
df = pd.read_csv(csv)
df['date'] = pd.to_datetime(df['date'])
df = df[df['date'] >= '2026-01-01']  # Only January 2026 onwards
```

## 📈 Interpreting Results

### High Bot Score Examples

| IP | Unique URLs | PHP Attempts | Entropy | Score | Why? |
|----|-------------|--------------|---------|-------|------|
| `45.142.x.x` | 20 | 15 | 4.2 | **36.9** | Mass PHP scanner |
| `103.x.x.x` | 12 | 0 | 3.8 | **13.6** | Random URL probing |

### Low Bot Score Examples (Likely Human)

| IP | Unique URLs | PHP Attempts | Entropy | Score | Why? |
|----|-------------|--------------|---------|-------|------|
| `192.168.x.x` | 3 | 0 | 0.8 | **3.1** | Typed wrong URL repeatedly |
| `10.x.x.x` | 1 | 0 | 0.0 | **0.5** | Bookmarked old page |

## 🐛 Troubleshooting

### ChromeDriver Issues (macOS)

If you see "Can not connect to Service":

```bash
# Make ChromeDriver executable
chmod +x ~/.wdm/drivers/chromedriver/*/chromedriver-mac-*/chromedriver

# Remove quarantine flag
xattr -d com.apple.quarantine ~/.wdm/drivers/chromedriver/*/chromedriver-mac-*/chromedriver
```

### Slow Scraping

The scraper adapts to page load speeds:
- Fast pages: 0.6 seconds between pages
- Slow pages: Waits up to 2 extra seconds if < 10 rows detected

To force faster (risk missing data):

Edit `real_scraper.py` line 89:

```python
time.sleep(0.3)  # Reduce from 0.6
```

### Empty Results

Common causes:
1. Not logged into WordPress when scraper runs
2. Redirection plugin not installed
3. No 404 logs exist yet

## 📝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the MIT License.

## 🙏 Acknowledgments

- Built for InterPro Wisconsin
- Uses [Redirection](https://redirection.me/) WordPress plugin data
- Powered by Selenium, Pandas, and Streamlit

## 📧 Contact

For questions or issues, please open a GitHub issue.

---

**Note**: This tool is designed for analyzing your own website's 404 logs. Always ensure you have proper authorization before scraping any website.
