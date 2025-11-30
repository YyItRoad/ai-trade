# Zig-Zag 算法集成计划

本文档描述了将 `calculate_zigzag` 函数集成到项目中的详细步骤。

## 步骤 1: 放置 Zig-Zag 函数代码

1.  打开 `zigzag_implementation.md` 文件，复制其中完整的 `calculate_zigzag` Python 函数代码。
2.  打开 `core/market_data.py` 文件。
3.  将复制的代码粘贴到 `fetch_all_kline_data_concurrently` 函数之后，`if __name__ == "__main__"` 块之前。

## 步骤 2: 修改数据获取逻辑以调用 Zig-Zag

我们需要在获取 K 线数据后，立即将其转换为 Zig-Zag 高低点。这需要在 `services/analysis_service.py` 文件中进行修改，因为那里是调用数据获取和 AI 分析的核心逻辑。

### 2.1 修改 `services/analysis_service.py`

1.  **导入新函数**: 在文件顶部添加导入语句：
    ```python
    from core.market_data import fetch_all_kline_data_concurrently, calculate_zigzag
    ```

2.  **修改 `run_analysis` 函数**: 找到 `run_analysis` 函数，在获取 `all_kline_data` 之后，添加数据转换和调用 Zig-Zag 的逻辑。

    **修改前**:
    ```python
    # (部分代码)
    all_kline_data = fetch_all_kline_data_concurrently(asset.symbol, asset.asset_type)
    if not any(all_kline_data.values()):
        logger.warning(f"未获取到 {asset.symbol} 的任何 K 线数据，跳过分析。")
        return
    
    # (后续调用 AI 模型的代码)
    ```

    **修改后**:
    ```python
    # (部分代码)
    all_kline_data = fetch_all_kline_data_concurrently(asset.symbol, asset.asset_type)
    if not any(all_kline_data.values()):
        logger.warning(f"未获取到 {asset.symbol} 的任何 K 线数据，跳过分析。")
        return

    # --- 新增代码开始 ---
    zigzag_points = {}
    for interval, klines in all_kline_data.items():
        if klines:
            # 将 K 线数据从列表列表转换为字典列表
            # K 线格式: [timestamp, open, high, low, close, volume]
            kline_dicts = [
                {"high": float(k[2]), "low": float(k[3])} for k in klines
            ]
            # 计算 Zig-Zag 点
            zigzag_points[interval] = calculate_zigzag(kline_dicts)
    
    # 将原始 K 线数据替换为 Zig-Zag 点
    data_to_send_to_ai = zigzag_points
    # --- 新增代码结束 ---

    # (后续调用 AI 模型的代码，确保将 `data_to_send_to_ai` 而不是 `all_kline_data` 传递给 AI)
    ```

## 步骤 3: 调整 AI 调用逻辑

在 `run_analysis` 函数中，确保传递给 AI 模型的数据是新生成的 `data_to_send_to_ai`（即 `zigzag_points`），而不是原始的 `all_kline_data`。

例如，如果原来的代码是：
```python
analysis_result = ai_client.analyze_data(data=all_kline_data, ...)
```

需要修改为：
```python
analysis_result = ai_client.analyze_data(data=data_to_send_to_ai, ...)
```

## 步骤 4: 更新提示词 (Prompt)

由于现在提供给 AI 的是 Zig-Zag 高低点数据，而不是完整的 K 线数据，您可能需要更新您的提示词（Prompt）以反映这一变化。

例如，您的提示词可以从：
> "请分析以下不同周期的 K 线数据..."

修改为：
> "请分析以下不同周期的 Zig-Zag 指标高低点序列..."

这可以确保 AI 模型正确理解输入数据的含义。

## 总结

完成以上步骤后，Zig-Zag 算法就成功集成到您的分析流程中了。系统将获取 K 线数据，将其转换为 Zig-Zag 高低点，然后将这些高低点发送给 AI 模型进行分析。