-- 字典表 (dictionary) 初始数据

-- 交易计划状态
INSERT INTO `dictionary` (`category`, `code`, `label`, `description`) VALUES
('trade_plan_status', 'ACTIVE', '激活', '交易计划已生成，等待市场条件触发。'),
('trade_plan_status', 'EXECUTED', '已执行', '交易计划已被手动或自动执行。'),
('trade_plan_status', 'CANCELLED', '已取消', '交易计划在触发前被手动取消。'),
('trade_plan_status', 'EXPIRED', '已过期', '交易计划因超时未达到入场条件而失效。');

-- 交易方向
INSERT INTO `dictionary` (`category`, `code`, `label`, `description`) VALUES
('direction', 'LONG', '做多', '预期资产价格上涨。'),
('direction', 'SHORT', '做空', '预期资产价格下跌。'),
('direction', 'NONE', '无方向', '当前市场状况不明确，建议观望。');

-- 趋势判断
INSERT INTO `dictionary` (`category`, `code`, `label`, `description`) VALUES
('trend', 'BULLISH', '看涨', '市场整体趋势向上。'),
('trend', 'BEARISH', '看跌', '市场整体趋势向下。'),
('trend', 'SIDEWAYS', '震荡', '市场价格在一定区间内波动，无明显方向。');