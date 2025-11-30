## Zig-Zag 算法实现

请将以下 Python 函数代码复制并粘贴到 `core/market_data.py` 文件中，建议放在 `fetch_all_kline_data_concurrently` 函数之后，`if __name__ == "__main__"` 块之前。

```python
def calculate_zigzag(kline_data: list[dict], threshold: float = 3.0) -> list[float]:
    """
    根据给定的K线数据和百分比阈值计算 Zig-Zag 指标。

    :param kline_data: K线数据列表，每个元素是一个包含 'high' 和 'low' 键的字典。
    :param threshold: 价格反转的百分比阈值。
    :return: 一个包含 Zig-Zag 高点和低点价格的列表。
    """
    if not kline_data:
        return []

    points = []
    trend = None  # None: 未定, 1: 上升, -1: 下降
    last_pivot_price = kline_data[0]['low']
    last_pivot_index = 0
    
    high_price = kline_data[0]['high']
    low_price = kline_data[0]['low']

    for i in range(1, len(kline_data)):
        current_high = kline_data[i]['high']
        current_low = kline_data[i]['low']

        if trend is None:
            if current_high > high_price:
                trend = 1
            elif current_low < low_price:
                trend = -1
        
        if trend == 1:  # 上升趋势
            if current_high > high_price:
                high_price = current_high
                last_pivot_index = i
            elif current_low < high_price * (1 - threshold / 100):
                points.append(high_price)
                trend = -1
                low_price = current_low
                last_pivot_price = high_price
                last_pivot_index = i
        
        elif trend == -1:  # 下降趋势
            if current_low < low_price:
                low_price = current_low
                last_pivot_index = i
            elif current_high > low_price * (1 + threshold / 100):
                points.append(low_price)
                trend = 1
                high_price = current_high
                last_pivot_price = low_price
                last_pivot_index = i

    # 添加最后一个 pivot 点
    if trend == 1:
        points.append(high_price)
    elif trend == -1:
        points.append(low_price)

    return points