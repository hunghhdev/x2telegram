-- Followers table - Stores Twitter accounts to follow
CREATE TABLE followers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    enabled BOOLEAN DEFAULT 1
);

-- Tweet cache table - Stores processed tweets
CREATE TABLE tweets_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    follower_id INTEGER,
    tweet_id TEXT,
    tweet_url TEXT,
    tweet_content TEXT,
    tweet_image BLOB,
    created_at DATETIME,
    inserted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_analyzed BOOLEAN DEFAULT 0,
    analysis_result TEXT,
    is_sent_to_telegram BOOLEAN DEFAULT 0,
    sent_at DATETIME,
    FOREIGN KEY(follower_id) REFERENCES followers(id)
);

-- Create indexes for performance optimization
CREATE INDEX idx_tweet_id ON tweets_cache(tweet_id);
CREATE INDEX idx_follower_id ON tweets_cache(follower_id);
CREATE INDEX idx_is_analyzed ON tweets_cache(is_analyzed);
CREATE INDEX idx_is_sent ON tweets_cache(is_sent_to_telegram);
