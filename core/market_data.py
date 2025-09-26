import requests
import json
import os
import argparse
from datetime import datetime
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.config import settings

BASE_URL = "https://trade.yangyang.fun/api/v1/kline"
logger = logging.getLogger(__name__)

def fetch_single_kline(symbol: str, interval: str, asset_type: int):
    """获取单个交易对、时间周期和资产类型的K线数据。"""
    if not settings.KLINE_API_SECRET_KEY:
        logger.error("K-line API 密钥未配置。无法获取市场数据。")
        return interval, []

    headers = {
        'accept': 'application/json',
        'Authorization': f'Basic {settings.KLINE_API_SECRET_KEY}'
    }
    
    params = {
        'type': asset_type,
        'symbol': symbol,
        'interval': interval,
        'limit': '100'
    }
    logger.info(
        f"发送 K-line 数据请求: symbol={symbol}, interval={interval}, type={asset_type}, "
        f"url={BASE_URL}"
    )
    try:
        response = requests.get(BASE_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        logger.info(f"成功获取 {symbol} - {interval} 的数据。")
        # 筛选每条K线，只保留前6个元素
        filtered_data = [kline[:6] for kline in response.json()]
        return interval, filtered_data
    except requests.exceptions.RequestException as e:
        logger.error(f"获取 {symbol} - {interval} 的数据失败: {e}")
        return interval, []

def fetch_all_kline_data_concurrently(symbol: str, asset_type: int):
    """
    为一个给定的资产类型并发地获取多个时间周期的K线数据。
    """
    intervals = ["15m", "1h", "4h"]
    combined_data = {}
    
    with ThreadPoolExecutor(max_workers=len(intervals)) as executor:
        future_to_interval = {
            executor.submit(fetch_single_kline, symbol, interval, asset_type): interval
            for interval in intervals
        }
        
        for future in as_completed(future_to_interval):
            interval, data = future.result()
            combined_data[interval] = data
            
    return combined_data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="为给定的交易对获取K线数据。")
    parser.add_argument("--symbol", type=str, default="BTCUSDT", help="要获取数据的交易对 (例如: BTCUSDT, ETHUSDT)。")
    parser.add_argument("--type", type=int, default=0, choices=[0, 1, 2], help="资产类型 (0: 现货, 1: U本位, 2: 币本位)。")
    args = parser.parse_args()
    
    symbol = args.symbol.upper()
    asset_type = args.type
    all_kline_data = fetch_all_kline_data_concurrently(symbol, asset_type)
    
    # 确保 'klins' 目录存在
    output_dir = "klins"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"{symbol}_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    # 将数据写入文件
    if any(all_kline_data.values()): # 仅在获取到数据时写入
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(all_kline_data, f, indent=4)
            print(f"\n成功将K线数据写入到 {filepath}")
        except IOError as e:
            print(f"\n写入文件 {filepath} 时出错: {e}")
    else:
        print("\n未获取到数据，跳过文件写入。")
