# TALL-E — Price Intelligence Platform

![Build](https://img.shields.io/github/actions/workflow/status/yourusername/tall-e/ci.yml?branch=main)
![License](https://img.shields.io/github/license/yourusername/tall-e)
![Python](https://img.shields.io/badge/backend-FastAPI-009688?logo=fastapi)
![Frontend](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB?logo=react)
![Database](https://img.shields.io/badge/database-PostgreSQL-4169E1?logo=postgresql)
![TypeScript](https://img.shields.io/badge/language-TypeScript-3178C6?logo=typescript)
![Status](https://img.shields.io/badge/status-in%20development-orange)

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
            ┌──────────────────────┐
            │   Chrome Extension   │
            └──────────┬───────────┘
                       │
            ┌──────────▼───────────┐
            │      Web Frontend    │
            │ React + Vite + TS    │
            └──────────┬───────────┘
                       │ REST API
            ┌──────────▼───────────┐
            │      FastAPI Backend │
            │  Pricing Engine      │
            │  Matching Engine     │
            └──────────┬───────────┘
                       │
            ┌──────────▼───────────┐
            │    PostgreSQL DB     │
            │ + PostGIS (optional) │
            └──────────────────────┘
