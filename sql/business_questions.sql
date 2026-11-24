-- All money stored as integer piastres. Delivered = recognized demo revenue.
-- Question 1: What changed month over month?
SELECT month, revenue, previous_revenue,
 ROUND(100.0*(revenue-previous_revenue)/NULLIF(previous_revenue,0),2) mom_pct
FROM monthly_revenue ORDER BY month;
-- Question 2: Which region has the highest return share?
SELECT region, COUNT(*) orders,
 ROUND(100.0*SUM(status='returned')/COUNT(*),2) return_pct
FROM orders GROUP BY region ORDER BY return_pct DESC;
-- Question 3: Who are repeat delivered-order customers?
SELECT customer_id, COUNT(*) delivered_orders, SUM(net_cents)/100.0 revenue
FROM orders WHERE status='delivered' GROUP BY customer_id HAVING COUNT(*)>1 ORDER BY revenue DESC;
-- Question 4: What is each category's contribution to delivered revenue?
WITH c AS (SELECT category,SUM(net_cents) revenue FROM orders WHERE status='delivered' GROUP BY category)
SELECT category,revenue/100.0 revenue_egp,ROUND(100.0*revenue/SUM(revenue) OVER(),2) share_pct FROM c ORDER BY revenue DESC;
