# Zig-Zag 算法测试计划

本文档提供了测试 `calculate_zigzag` 函数及其在项目中集成的详细步骤。

## 1. 单元测试 (推荐)

单元测试是验证算法逻辑正确性的最佳方式。建议在项目根目录下创建一个 `tests` 文件夹（如果尚不存在），并在其中创建一个名为 `test_zigzag.py` 的文件。

### `tests/test_zigzag.py` 文件内容示例:

```python
import unittest
import sys
import os

# 将项目根目录添加到 Python 路径中，以便导入 core 模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.market_data import calculate_zigzag

class TestZigZag(unittest.TestCase):

    def test_simple_zigzag(self):
        """测试一个简单的上升后下降的场景"""
        kline_data = [
            {'high': 102, 'low': 100},  # 初始点
            {'high': 105, 'low': 103},  # 上升
            {'high': 110, 'low': 108},  # 最高点
            {'high': 108, 'low': 106},  # 开始下降 (110 -> 106, -3.6%, 超过 3% 阈值)
            {'high': 105, 'low': 103},  # 继续下降
            {'high': 102, 'low': 100},  # 最低点
            {'high': 104, 'low': 102},  # 开始反弹 (100 -> 104, +4%, 超过 3% 阈值)
        ]
        expected_points = [110, 100]
        result = calculate_zigzag(kline_data, threshold=3.0)
        self.assertEqual(result, expected_points)

    def test_no_reversal(self):
        """测试没有足够反转的场景"""
        kline_data = [
            {'high': 102, 'low': 100},
            {'high': 103, 'low': 101},
            {'high': 104, 'low': 102},
        ]
        # 预期只有一个点，即最后一个高点
        expected_points = [104]
        result = calculate_zigzag(kline_data, threshold=3.0)
        self.assertEqual(result, expected_points)

    def test_empty_input(self):
        """测试空输入"""
        kline_data = []
        expected_points = []
        result = calculate_zigzag(kline_data, threshold=3.0)
        self.assertEqual(result, expected_points)

if __name__ == '__main__':
    unittest.main()
```

**如何运行单元测试:**

1.  确保您已经按照 `zigzag_integration_plan.md` 将 `calculate_zigzag` 函数添加到了 `core/market_data.py` 中。
2.  在终端中，导航到项目根目录。
3.  运行以下命令：
    ```bash
    python -m unittest tests/test_zigzag.py
    ```
4.  观察输出，确保所有测试都通过。

## 2. 集成测试 (手动)

集成测试用于验证 Zig-Zag 算法在真实数据和应用流程中的表现。我们可以临时修改 `core/market_data.py` 的 `if __name__ == "__main__"` 部分来执行这个测试。

### 修改 `core/market_data.py` 以进行测试:

1.  **导入 `calculate_zigzag`**: 确保它在文件顶部被导入（如果尚未导入）。
2.  **修改 `main` 块**: 找到文件底部的 `if __name__ == "__main__"` 块，并将其临时替换为以下代码：

    ```python
    if __name__ == "__main__":
        # --- 集成测试代码 ---
        
        # 1. 获取真实 K 线数据
        test_symbol = "BTCUSDT"
        test_asset_type = 0  # 现货
        all_kline_data = fetch_all_kline_data_concurrently(test_symbol, test_asset_type)
        
        # 2. 选择一个时间周期进行测试 (例如 '15m')
        interval_to_test = "15m"
        klines = all_kline_data.get(interval_to_test)
        
        if not klines:
            print(f"未能获取到 {test_symbol} - {interval_to_test} 的 K 线数据，无法进行测试。")
        else:
            print(f"--- 原始 K 线数据 ({interval_to_test}) ---")
            print(klines[:5]) # 打印前 5 条 K 线看看格式
            
            # 3. 转换数据格式
            kline_dicts = [
                {"high": float(k[2]), "low": float(k[3])} for k in klines
            ]
            
            # 4. 计算 Zig-Zag
            zigzag_points = calculate_zigzag(kline_dicts, threshold=3.0)
            
            print(f"\n--- 计算出的 Zig-Zag 高低点 ({len(zigzag_points)} 个) ---")
            print(zigzag_points)
            
            print("\n测试完成。")
    ```

**如何运行集成测试:**

1.  在终端中，导航到项目根目录。
2.  运行以下命令：
    ```bash
    python core/market_data.py
    ```
3.  **观察输出**:
    *   检查是否成功获取了 K 线数据。
    *   查看打印出的 Zig-Zag 高低点列表。
    *   根据您对市场价格走势的直观感受，判断这些高低点是否合理。
4.  **测试完成后**: 记得将 `core/market_data.py` 文件底部的 `if __name__ == "__main__"` 块恢复到其原始状态，以便 `manage.py` 等脚本可以正常使用它。

完成以上测试后，您就可以对 Zig-Zag 算法的正确性和集成效果充满信心。