document.addEventListener('DOMContentLoaded', () => {
    // --- 身份验证检查 ---
    const STORAGE_KEY = 'app_config_key';
    if (!localStorage.getItem(STORAGE_KEY)) {
        window.location.href = '/login';
        return; // 如果未通过身份验证，则停止脚本执行
    }
    // --- 状态变量 ---
    let allAssets = []; // 用于缓存所有从 API 获取的资产

    // --- DOM 元素 ---
    const tableBody = document.getElementById('assets-table-body');
    const typeFilter = document.getElementById('type-filter');
    
    // 模态框元素
    const addAssetModal = document.getElementById('add-asset-modal');
    const addAssetBtn = document.getElementById('add-asset-btn');
    const addAssetCloseButton = addAssetModal.querySelector('.close-button');
    const addAssetForm = document.getElementById('add-asset-form');
    const newAssetSymbolInput = document.getElementById('new-asset-symbol');
    const newAssetTypeSelect = document.getElementById('new-asset-type');
    const manageStatusMessage = document.getElementById('manage-status-message');

    // 定时任务模态框元素
    const scheduleModal = document.getElementById('set-schedule-modal');
    const scheduleCloseButton = scheduleModal.querySelector('.close-button');
    const setScheduleForm = document.getElementById('set-schedule-form');
    const scheduleAssetSymbol = document.getElementById('schedule-asset-symbol');
    const scheduleCronStringInput = document.getElementById('schedule-cron-string');
    const scheduleAssetIdInput = document.getElementById('schedule-asset-id');
    const scheduleStatusMessage = document.getElementById('schedule-status-message');

    // --- 映射关系 ---
    const typeStringToNum = { 'SPOT': 0, 'USD_M': 1, 'COIN_M': 2 };
    const typeNumToString = { 0: 'SPOT', 1: 'USD_M', 2: 'COIN_M' };
    const assetTypeMap = {
        'SPOT': '现货',
        'USD_M': 'U本位合约',
        'COIN_M': '币本位合约'
    };

    // --- 函数 ---

    async function fetchAssets() {
        try {
            const response = await fetch('/api/assets');
            if (!response.ok) {
                throw new Error('获取资产列表失败');
            }
            allAssets = await response.json();
            renderTable(); // 使用当前过滤器渲染表格
        } catch (error) {
            tableBody.innerHTML = `<tr><td colspan="5" class="error">加载资产出错: ${error.message}</td></tr>`;
        }
    }

    function renderTable() {
        const filterValue = typeFilter.value;
        
        const filteredAssets = filterValue === 'ALL'
            ? allAssets
            : allAssets.filter(asset => {
                const typeAsNum = typeStringToNum[filterValue];
                return asset.type === typeAsNum;
            });

        tableBody.innerHTML = ''; // 清空当前表格
        if (filteredAssets.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5">未找到任何资产。</td></tr>';
            return;
        }

        filteredAssets.forEach(asset => {
            const row = document.createElement('tr');
            const typeAsString = typeNumToString[asset.type] || '未知';
            const assetTypeText = assetTypeMap[typeAsString] || typeAsString;
            const scheduleDisplay = asset.schedule_cron
                ? `<code>${asset.schedule_cron}</code>`
                : '<span class="not-set">未设置</span>';

            row.innerHTML = `
                <td>${asset.id}</td>
                <td>${asset.symbol}</td>
                <td>${assetTypeText}</td>
                <td>${scheduleDisplay}</td>
                <td>
                    <button class="trigger-analysis-btn" data-symbol="${asset.symbol}" data-type="${typeAsString}">立即执行</button>
                    <button class="set-schedule-btn" data-id="${asset.id}" data-symbol="${asset.symbol}" data-cron="${asset.schedule_cron || ''}">设置定时</button>
                    <button class="delete-asset-btn" data-id="${asset.id}" data-symbol="${asset.symbol}">删除</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    // --- 模态框控制 ---
    function openAddAssetModal() {
        addAssetModal.style.display = 'block';
    }

    function closeAddAssetModal() {
        addAssetModal.style.display = 'none';
        addAssetForm.reset();
        manageStatusMessage.textContent = '';
    }

    function openScheduleModal(asset) {
        scheduleAssetIdInput.value = asset.id;
        scheduleAssetSymbol.textContent = asset.symbol;
        scheduleCronStringInput.value = asset.cron;
        scheduleStatusMessage.textContent = '';
        scheduleModal.style.display = 'block';
    }

    function closeScheduleModal() {
        scheduleModal.style.display = 'none';
        setScheduleForm.reset();
        scheduleStatusMessage.textContent = '';
    }

    // --- 事件监听器 ---

    // 添加资产模态框事件
    addAssetBtn.addEventListener('click', openAddAssetModal);
    addAssetCloseButton.addEventListener('click', closeAddAssetModal);
    
    // 定时任务模态框事件
    scheduleCloseButton.addEventListener('click', closeScheduleModal);

    // 用于关闭模态框的窗口级点击监听器
    window.addEventListener('click', (event) => {
        if (event.target === addAssetModal) {
            closeAddAssetModal();
        }
        if (event.target === scheduleModal) {
            closeScheduleModal();
        }
    });

    // 筛选事件
    typeFilter.addEventListener('change', renderTable);

    // 表单提交
    addAssetForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const symbol = newAssetSymbolInput.value.trim().toUpperCase();
        const typeStr = newAssetTypeSelect.value;
        const type = typeStringToNum[typeStr];

        if (!symbol) {
            manageStatusMessage.textContent = '交易对符号不能为空。';
            manageStatusMessage.style.color = 'red';
            return;
        }

        try {
            const response = await fetch('/api/assets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbol, type })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '添加资产失败');
            }

            manageStatusMessage.textContent = `资产 ${symbol} 添加成功。`;
            manageStatusMessage.style.color = 'green';
            
            // 重新获取所有数据并在短暂延迟后关闭模态框
            await fetchAssets();
            setTimeout(closeAddAssetModal, 1500);

        } catch (error) {
            manageStatusMessage.textContent = `错误: ${error.message}`;
            manageStatusMessage.style.color = 'red';
        }
    });

    // 表格操作 (使用事件委托)
    tableBody.addEventListener('click', async (event) => {
        const target = event.target;

        // 处理删除
        if (target.classList.contains('delete-asset-btn')) {
            const assetId = target.dataset.id;
            const assetSymbol = target.dataset.symbol;
            if (!confirm(`确定要删除资产 ${assetSymbol} (ID: ${assetId}) 吗?`)) {
                return;
            }

            try {
                const response = await fetch(`/api/assets/${assetId}`, { method: 'DELETE' });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || '删除资产失败');
                }
                await fetchAssets();
            } catch (error) {
                alert(`删除错误: ${error.message}`);
            }
        }

        // 处理设置定时任务
        if (target.classList.contains('set-schedule-btn')) {
            const asset = {
                id: target.dataset.id,
                symbol: target.dataset.symbol,
                cron: target.dataset.cron
            };
            openScheduleModal(asset);
        }

        // 处理触发分析
        if (target.classList.contains('trigger-analysis-btn')) {
            const symbol = target.dataset.symbol;
            const type = target.dataset.type;
            if (!confirm(`确定要为 ${symbol} (类型: ${type}) 手动触发一次分析任务吗？`)) {
                return;
            }
            try {
                target.textContent = '触发中...';
                target.disabled = true;

                const response = await fetch(`/api/trigger-analysis/${type}/${symbol}`, { method: 'POST' });
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || '触发分析失败');
                }
                
                const result = await response.json();
                alert(result.message);

            } catch (error) {
                alert(`触发错误: ${error.message}`);
            } finally {
                target.textContent = '立即执行';
                target.disabled = false;
            }
        }
    });

    // 定时任务表单提交
    setScheduleForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const assetId = scheduleAssetIdInput.value;
        const cronString = scheduleCronStringInput.value.trim();

        scheduleStatusMessage.textContent = '正在保存...';
        scheduleStatusMessage.style.color = 'inherit';

        try {
            const response = await fetch(`/api/assets/${assetId}/schedule`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ schedule_cron: cronString === '' ? null : cronString })
            });

            if (!response.ok) {
                const errorData = await response.json();
                // 尝试解析更具体的错误信息
                let detail = '保存失败';
                if (errorData.detail && Array.isArray(errorData.detail) && errorData.detail.length > 0) {
                    detail = errorData.detail[0].msg || detail;
                } else if (typeof errorData.detail === 'string') {
                    detail = errorData.detail;
                }
                throw new Error(detail);
            }

            scheduleStatusMessage.textContent = '保存成功！';
            scheduleStatusMessage.style.color = 'green';

            await fetchAssets();
            setTimeout(closeScheduleModal, 1500);

        } catch (error) {
            scheduleStatusMessage.textContent = `错误: ${error.message}`;
            scheduleStatusMessage.style.color = 'red';
        }
    });

    // --- 初始化 ---
    fetchAssets();
});