# TALL-E — Price Intelligence Platform

![Backend](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi&logoColor=white)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB?logo=react&logoColor=black)
![Database](https://img.shields.io/badge/database-PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Cache](https://img.shields.io/badge/cache%2Fqueue-Redis-DC382D?logo=redis&logoColor=white)
![Worker](https://img.shields.io/badge/worker-scraper%20%2F%20jobs-6E40C9)
![Infrastructure](https://img.shields.io/badge/infrastructure-Docker-2496ED?logo=docker&logoColor=white)
![Orchestration](https://img.shields.io/badge/orchestration-Docker%20Compose-384D54?logo=docker&logoColor=white)
![CI](https://img.shields.io/github/actions/workflow/status/yourusername/tall-e/ci.yml?branch=main)
![Language](https://img.shields.io/badge/language-TypeScript-3178C6?logo=typescript&logoColor=white)
![Status](https://img.shields.io/badge/status-in%20development-orange)
![License](https://img.shields.io/github/license/yourusername/tall-e)



---

## Overview

**TALL-E** is a real-time price comparison platform that helps users find the best deals across beauty, pharmacy, and technology products.

It is available as:
- A web application
- A Chrome extension that integrates directly into retailer websites

TALL-E aggregates product data from multiple retailers, normalizes inconsistent listings, and computes true comparable prices so users can make informed purchasing decisions.

---

## Features

- **Cross-Retailer Price Comparison**
  - Compare identical products across multiple stores
  - Detect duplicates despite inconsistent naming

- **Price Normalization**
  - Unit price calculations (e.g. per ml, per gram)
  - Multi-buy decomposition ("2 for $30" → per-unit price)

- **Location-Aware Results**
  - Filter by nearby stores
  - Availability-based ranking

- **Chrome Extension Integration**
  - Detect products on retailer pages
  - Display cheaper alternatives inline

- **Product Matching System**
  - Parse unstructured product names into structured attributes
  - Match across retailers using heuristics and rules

- **Planned Features**
  - Price history tracking
  - Discount validation
  - Price alerts

---

## Architecture

```text
                 ┌─────────────────────────┐
                 │      Chrome Extension   │
                 │  (page detection + UI)  │
                 └────────────┬────────────┘
                              │ HTTPS (REST)
                              │
                 ┌────────────▼────────────┐
                 │        Web Frontend      │
                 │   React + Vite + TS      │
                 └────────────┬────────────┘
                              │ HTTPS (REST)
                              │
                 ┌────────────▼────────────┐
                 │      FastAPI Backend     │
                 │  - Search / Compare API  │
                 │  - Matching / Ranking    │
                 │  - Pricing Normalization │
                 └───────┬─────────┬────────┘
                         │         │
                  Cache/Queue      │ SQL
                         │         │
               ┌─────────▼───┐   ┌▼────────────────┐
               │    Redis     │   │   PostgreSQL     │
               │ (cache/queue)│   │ (+ PostGIS opt.) │
               └───────┬──────┘   └─────────────────┘
                       │
                       │ jobs (scrape/refresh/match)
               ┌───────▼────────────────────┐
               │    Worker / Scraper Service │
               │  - ingestion pipelines      │
               │  - retailer adapters        │
               │  - dedupe + enrichment      │
               └────────────────────────────┘

      All services run locally via Docker Compose (dev) and can be deployed as containers (prod).

