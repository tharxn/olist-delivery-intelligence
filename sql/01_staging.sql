-- Raw identifiers and postcodes stay strings; source timestamps have no timezone.
CREATE OR REPLACE TABLE staging.orders AS
SELECT order_id, customer_id, order_status,
       try_cast(order_purchase_timestamp AS TIMESTAMP) AS purchased_at,
       try_cast(order_approved_at AS TIMESTAMP) AS approved_at,
       try_cast(order_delivered_carrier_date AS TIMESTAMP) AS handed_to_carrier_at,
       try_cast(order_delivered_customer_date AS TIMESTAMP) AS delivered_at,
       try_cast(order_estimated_delivery_date AS TIMESTAMP) AS estimated_at
FROM raw.orders;

CREATE OR REPLACE TABLE staging.customers AS
SELECT customer_id, customer_unique_id, customer_zip_code_prefix,
       customer_city, customer_state FROM raw.customers;

CREATE OR REPLACE TABLE staging.sellers AS
SELECT seller_id, seller_zip_code_prefix, seller_city, seller_state FROM raw.sellers;

CREATE OR REPLACE TABLE staging.products AS
SELECT p.product_id, p.product_category_name,
       coalesce(t.product_category_name_english, p.product_category_name, 'unknown') AS category
FROM raw.products p LEFT JOIN raw.translations t USING (product_category_name);

CREATE OR REPLACE TABLE staging.items AS
SELECT order_id, try_cast(order_item_id AS INTEGER) AS order_item_id,
       product_id, seller_id,
       try_cast(shipping_limit_date AS TIMESTAMP) AS shipping_limit_at,
       try_cast(price AS DECIMAL(18,2)) AS item_value_brl,
       try_cast(freight_value AS DECIMAL(18,2)) AS freight_value_brl
FROM raw.items;

CREATE OR REPLACE TABLE staging.payments AS
SELECT order_id, try_cast(payment_sequential AS INTEGER) AS payment_sequential,
       payment_type, try_cast(payment_installments AS INTEGER) AS payment_installments,
       try_cast(payment_value AS DECIMAL(18,2)) AS payment_value_brl
FROM raw.payments;

-- One review per order: latest answer/creation, followed by deterministic tie-breaks.
CREATE OR REPLACE TABLE staging.reviews AS
SELECT order_id, review_id, try_cast(review_score AS INTEGER) AS review_score,
       try_cast(review_creation_date AS TIMESTAMP) AS review_created_at,
       try_cast(review_answer_timestamp AS TIMESTAMP) AS review_answered_at
FROM raw.reviews
QUALIFY row_number() OVER (
    PARTITION BY order_id
    ORDER BY coalesce(try_cast(review_answer_timestamp AS TIMESTAMP),
                      try_cast(review_creation_date AS TIMESTAMP)) DESC NULLS LAST,
             review_id DESC, try_cast(review_score AS INTEGER) DESC
) = 1;
