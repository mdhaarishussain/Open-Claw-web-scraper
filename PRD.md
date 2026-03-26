
# Product Requirements Document (PRD): Heartisans Autonomous Data Pipeline

## 1. Project Overview
**Objective:** Develop a fully autonomous, local agent-driven data pipeline to collect, structure, and store a 10,000-row dataset for the Heartisans luxury and antique price prediction model. 
**Problem Statement:** Paid scraping APIs (like Apify) are cost-prohibitive for large-scale extraction, and target sites employ heavy anti-bot protections (Cloudflare, Turnstile). Furthermore, raw scraped data is unstructured, whereas the ML model requires 15 strictly formatted features.
**Solution:** A self-hosted orchestration loop using OpenClaw to manage state and navigation, paired with Scrapling for stealth extraction, and a lightweight LLM/NLP step for strict JSON structuring.

## 2. Tech Stack & Architecture
* **Agent Orchestrator:** OpenClaw (Local)
* **Scraping Engine:** `Scrapling` (Python-based, specifically the `StealthyFetcher` for bypassing bot protection)
* **Data Structuring:** Local LLM (e.g., Ollama) or lightweight API (OpenAI/Anthropic) integrated as an OpenClaw tool.
* **Storage:** Local SQLite database or heavily structured CSV.
* **Environment:** Python 3.10+

## 3. Core Workflow (The Autonomous Loop)
The IDE should build a system that executes the following loop without human intervention:
1.  **Target Acquisition:** Read from a seed list of base URLs (e.g., specific categories on Chrono24, 1stDibs, or eBay Sold items).
2.  **Stealth Navigation:** Use Scrapling to render the page, bypass CAPTCHAs, and extract raw HTML/Text of individual product listings.
3.  **NLP Extraction:** Pass the raw listing text to the structuring agent with a strict system prompt to extract the 15 required features.
4.  **Validation & Storage:** Verify the output matches the required schema. If valid, append to the database. If invalid, retry or discard.
5.  **Pagination/Iteration:** Automatically find the "Next Page" link and repeat until the target row count is hit.

## 4. Data Schema Requirements
The AI IDE must create data models (e.g., using Pydantic) to strictly enforce these 15 features during the NLP extraction phase. 

1.  **Material used** (String)
2.  **Any valuable gem** (String/None)
3.  **Expensive material** (String/None)
4.  **Origin** (String)
5.  **Date of manufacture** (String/Integer Year)
6.  **Any defects** (Boolean/String description)
7.  **Scratches** (Boolean)
8.  **Colour** (String)
9.  **Current Market Price** (Float - Must be normalized to a single currency)
10. **Seller reputation** (Float/String - Normalized metric)
11. **Dimensions** (String - Height, Width)
12. **Weight** (String/Float)
13. **Handwork/Machine work** (Categorical: Handwork, Machine work, Unknown)
14. **Any specific Brand** (String - e.g., Gucci, LV, Tiffany)
15. **Limited Edition Collectibles** (Boolean)

## 5. Implementation Phases (For the AI IDE)
* **Phase 1: Project Initialization.** Set up the Python virtual environment, install OpenClaw, Scrapling, Pydantic, and SQLite libraries. Create the directory structure.
* **Phase 2: Scrapling Engine.** Write a standalone Python module utilizing Scrapling's `StealthyFetcher` that accepts a URL and returns raw page text. Include error handling for timeouts and blocks.
* **Phase 3: Schema & Extraction Tool.** Create the Pydantic models for the 15 columns. Write the OpenClaw Tool/Skill that takes raw text, passes it to the LLM with the Pydantic schema, and returns structured JSON.
* **Phase 4: The Orchestrator.** Write the main execution script (`main.py`) that initializes OpenClaw, provides it with the seed URLs, and commands it to begin the autonomous loop.

## 6. Constraints & Fallbacks
* **No Paid Scraping APIs:** The system must not rely on Apify, ScrapingBee, etc.
* **Rate Limiting:** The loop must include randomized human-like delays (e.g., `time.sleep(random.uniform(2, 7))`) between requests to avoid IP bans.
* **Data Integrity:** If the NLP extraction cannot confidently determine the `Current Market Price`, the row must be discarded. Price is the target variable and cannot be hallucinated.

***
