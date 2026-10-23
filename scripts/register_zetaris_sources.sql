-- =============================================================================
-- Zetaris Virtual Table Registration Script
-- Digital Doppelganger: Phase 1 Data Sources
-- =============================================================================
-- Run this script against your Zetaris Virtual Data Warehouse instance
-- to register the synthetic data sources as queryable virtual tables.
--
-- Replace <STORAGE_BASE_PATH> with your actual mounted storage or object store URI:
-- e.g., file:///opt/data/sample/ OR s3://my-bucket/digital-doppelganger/sample/
-- =============================================================================

-- 1. Profile Fields
CREATE OR REPLACE VIRTUAL TABLE profile_fields (
    profile_id VARCHAR(10),
    field_name VARCHAR(50),
    field_value VARCHAR(255),
    source_platform VARCHAR(50),
    updated_at VARCHAR(30)
)
WITH (
    format = 'CSV',
    header = true,
    location = '<STORAGE_BASE_PATH>/profile_fields.csv'
);

-- 2. Strava Activities
CREATE OR REPLACE VIRTUAL TABLE strava_activities (
    profile_id VARCHAR(10),
    activity_id VARCHAR(50),
    activity_type VARCHAR(30),
    start_time VARCHAR(30),
    end_time VARCHAR(30),
    start_lat DOUBLE,
    start_lon DOUBLE,
    distance_km DOUBLE,
    route_summary VARCHAR(255)
)
WITH (
    format = 'CSV',
    header = true,
    location = '<STORAGE_BASE_PATH>/strava_activities.csv'
);

-- 3. Food Delivery Orders
CREATE OR REPLACE VIRTUAL TABLE food_orders (
    profile_id VARCHAR(10),
    order_id VARCHAR(50),
    timestamp VARCHAR(30),
    delivery_address VARCHAR(255),
    items VARCHAR(255),
    restaurant_name VARCHAR(100),
    total_amount DOUBLE
)
WITH (
    format = 'CSV',
    header = true,
    location = '<STORAGE_BASE_PATH>/food_orders.csv'
);

-- 4. Calendar Events
CREATE OR REPLACE VIRTUAL TABLE calendar_events (
    profile_id VARCHAR(10),
    event_id VARCHAR(50),
    title VARCHAR(150),
    start_time VARCHAR(30),
    end_time VARCHAR(30),
    location VARCHAR(255),
    description VARCHAR(255)
)
WITH (
    format = 'CSV',
    header = true,
    location = '<STORAGE_BASE_PATH>/calendar_events.csv'
);

-- 5. Social Posts
CREATE OR REPLACE VIRTUAL TABLE social_posts (
    profile_id VARCHAR(10),
    post_id VARCHAR(50),
    timestamp VARCHAR(30),
    platform VARCHAR(50),
    text_content VARCHAR(500),
    location_tag VARCHAR(100),
    media_type VARCHAR(30)
)
WITH (
    format = 'CSV',
    header = true,
    location = '<STORAGE_BASE_PATH>/social_posts.csv'
);

-- 6. Pharmacy Orders
CREATE OR REPLACE VIRTUAL TABLE pharmacy_orders (
    profile_id VARCHAR(10),
    order_id VARCHAR(50),
    timestamp VARCHAR(30),
    item_category VARCHAR(150),
    prescriber_specialty VARCHAR(100),
    delivery_address VARCHAR(255)
)
WITH (
    format = 'CSV',
    header = true,
    location = '<STORAGE_BASE_PATH>/pharmacy_orders.csv'
);
