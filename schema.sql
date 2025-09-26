CREATE TABLE IF NOT EXISTS trade_analysis (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '记录ID',
    asset VARCHAR(50) NOT NULL COMMENT '资产符号',
    timestamp DATETIME NOT NULL COMMENT '分析时间戳',
    conclusion VARCHAR(50) COMMENT '交易结论 (例如 OPEN_POSITION)',
    direction VARCHAR(10) COMMENT '方向 (LONG/SHORT)',
    confidence FLOAT COMMENT '置信度 (0.0 to 1.0)',
    risk_reward_ratio VARCHAR(20) COMMENT '风险回报比',
    entry_point DECIMAL(20, 8) COMMENT '入场点',
    stop_loss DECIMAL(20, 8) COMMENT '止损点',
    take_profit_1 DECIMAL(20, 8) COMMENT '第一止盈点',
    take_profit_2 DECIMAL(20, 8) COMMENT '第二止盈点',
    analysis_summary TEXT COMMENT '分析摘要',
    wave_analysis_4h TEXT COMMENT '4小时浪型分析',
    wave_analysis_1h TEXT COMMENT '1小时浪型分析',
    wave_analysis_15m TEXT COMMENT '15分钟浪型分析',
    rationale TEXT COMMENT '理由和逻辑',
    raw_response JSON COMMENT 'AI返回的原始JSON响应',
    INDEX idx_asset_timestamp (asset, timestamp)
) COMMENT='交易分析结果表';

CREATE TABLE IF NOT EXISTS assets (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '资产ID',
    symbol VARCHAR(50) NOT NULL COMMENT '交易对符号',
    `type` INT NOT NULL COMMENT '资产类型: 0(现货), 1(U本位), 2(币本位)',
    schedule_cron VARCHAR(100) NULL DEFAULT NULL COMMENT '用于任务调度的Cron表达式, NULL表示禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    UNIQUE KEY `idx_symbol_type` (`symbol`, `type`)
) COMMENT='可供分析的资产配置表';