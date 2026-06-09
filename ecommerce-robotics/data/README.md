# 数据源说明 | Data Sources

## Kaggle 源数据

### 1. E-Commerce Transactions Dataset
- **Kaggle地址:** https://www.kaggle.com/datasets/zahidulislamturjo/e-commerce-transactions-dataset
- **原始文件:** `kaggle_raw/customers.csv`, `orders.csv`, `order_items.csv`, `products.csv`
- **数据规模:** 3000客户 × 4000订单 × 9954订单明细 × 2000产品
- **说明:** 真实电商交易数据，包含客户信息、订单记录、产品分类、销售额和利润
- **用途:** 支撑电商仓储机器人需求分析中的订单量、品类分布等基础数据

## 行业报告综合数据 (基于Kaggle源数据+公开报告)

> 以下CSV文件基于 Kaggle 电商交易数据 + IFR、McKinsey、LogisticsIQ 公开行业报告综合整理

| 文件 | 说明 | 来源 |
|------|------|------|
| market_size_trend.csv | 全球仓储机器人市场规模(2020-2027) | IFR + LogisticsIQ 2025 |
| robot_types.csv | 各类型仓储机器人市场份额与增长率 | LogisticsIQ Market Report |
| regional_adoption.csv | 10个地区电商机器人采用率对比 | IFR World Robotics 2025 |
| company_market_share.csv | 仓储机器人头部企业市场份额 | McKinsey + 各公司年报 |
| roi_analysis.csv | 5类仓储机器人投资回报分析 | 行业综合数据 |
| scenario_distribution.csv | 电商仓储机器人应用场景分布 | IFR + McKinsey |
| future_prediction.csv | 2025-2030年市场结构预测 | LogisticsIQ 预测模型 |
| china_vs_global.csv | 中国 vs 全球市场规模对比 | IFR + 中国机器人产业联盟 |

## 数据引用格式 (PPT最后一页建议)
```
数据来源:
- Kaggle: E-Commerce Transactions Dataset (zahidulislamturjo)
- International Federation of Robotics (IFR) - World Robotics 2025
- McKinsey & Company - Warehouse Automation Report
- LogisticsIQ - Warehouse Automation Market Report 2025
```
