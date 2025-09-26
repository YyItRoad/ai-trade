document.addEventListener('DOMContentLoaded', () => {
    // --- 身份验证检查 ---
    const STORAGE_KEY = 'app_config_key';
    if (!localStorage.getItem(STORAGE_KEY)) {
        window.location.href = '/login';
        return; // 如果未通过身份验证，则停止脚本执行
    }
    // DOM 元素
    const tableBody = document.getElementById('analysis-table-body');
    const pageInfo = document.getElementById('page-info');
    const firstPageBtn = document.getElementById('first-page');
    const prevPageBtn = document.getElementById('prev-page');
    const nextPageBtn = document.getElementById('next-page');
    const lastPageBtn = document.getElementById('last-page');
    const statusMessage = document.getElementById('status-message');
    const assetSelector = document.getElementById('asset-selector');
    const queryBtn = document.getElementById('query-btn');
    
    const modal = document.getElementById('details-modal');
    const modalData = document.getElementById('modal-data');
    const closeButton = document.querySelector('.close-button');

    // 状态变量
    let currentPage = 1;
    let totalPages = 1;
    const pageSize = 20;
    let currentRecords = new Map(); // 使用 Map 按 ID 存储完整的记录对象

    // --- 数据获取与渲染 ---

    async function loadAssets() {
        try {
            const response = await fetch('/api/asset-symbols');
            if (!response.ok) throw new Error('加载资产列表失败');
            const assets = await response.json();
            
            assetSelector.innerHTML = '<option value="">所有资产</option>';
            assets.forEach(asset => {
                const option = document.createElement('option');
                option.value = asset;
                option.textContent = asset;
                assetSelector.appendChild(option);
            });
            
            // 资产加载后初次获取数据
            fetchData();
        } catch (error) {
            console.error("加载资产列表失败:", error);
            assetSelector.innerHTML = '<option value="">加载资产列表出错</option>';
        }
    }

    async function fetchData(page = 1) {
        const selectedAsset = assetSelector.value;
        let url = `/api/analysis-history?page=${page}&size=${pageSize}`;
        if (selectedAsset) {
            url += `&asset=${selectedAsset}`;
        }

        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const result = await response.json();
            updateTable(result.data);
            updatePagination(result.page, result.total_pages);
        } catch (error) {
            console.error("获取分析数据失败:", error);
            tableBody.innerHTML = `<tr><td colspan="9" style="text-align:center; color: red;">数据加载失败。</td></tr>`;
        }
    }

    function updateTable(records) {
        const conclusionMap = {
            'OPEN_POSITION': '开仓',
            'CLOSE_POSITION': '平仓',
            'HOLD_POSITION': '持仓',
            'STAY_FLAT': '观望'
        };

        tableBody.innerHTML = ''; // 清空现有行
        currentRecords.clear(); // 在重新填充之前清除 map

        if (!records || records.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="9" style="text-align:center;">无可用数据。</td></tr>`;
            return;
        }

        records.forEach(record => {
            currentRecords.set(record.id.toString(), record); // 按 ID 存储记录

            const row = document.createElement('tr');
            
            const formatPrice = (price) => {
                if (price === null || price === undefined) return '无';
                return Number(price);
            };

            const formatConfidence = (confidence) => {
                if (confidence === null || confidence === undefined) return '无';
                return `${(confidence * 100).toFixed(0)}%`;
            };

            const directionMap = {
                'LONG': '多',
                'SHORT': '空'
            };
            const directionClass = record.direction === 'LONG' ? 'direction-long' : (record.direction === 'SHORT' ? 'direction-short' : '');
            const conclusionText = conclusionMap[record.conclusion] || record.conclusion || '无';
            const directionText = directionMap[record.direction] || record.direction || '无';

            row.innerHTML = `
                <td>${new Date(record.timestamp).toLocaleString()}</td>
                <td>${record.asset}</td>
                <td>${conclusionText}</td>
                <td class="${directionClass}">${directionText}</td>
                <td>${formatConfidence(record.confidence)}</td>
                <td>${formatPrice(record.entry_point)}</td>
                <td>${formatPrice(record.stop_loss)}</td>
                <td>${formatPrice(record.take_profit_1)}</td>
                <td><button class="details-button" data-record-id="${record.id}">详情</button></td>
            `;
            tableBody.appendChild(row);
        });
    }

    function updatePagination(page, total) {
        currentPage = page;
        totalPages = total > 0 ? total : 1;
        pageInfo.textContent = `第 ${currentPage} 页 / 共 ${totalPages} 页`;

        firstPageBtn.disabled = currentPage === 1;
        prevPageBtn.disabled = currentPage === 1;
        nextPageBtn.disabled = currentPage === totalPages;
        lastPageBtn.disabled = currentPage === totalPages;
    }

    // --- 事件监听器 ---

    firstPageBtn.addEventListener('click', () => fetchData(1));
    prevPageBtn.addEventListener('click', () => fetchData(currentPage - 1));
    nextPageBtn.addEventListener('click', () => fetchData(currentPage + 1));
    lastPageBtn.addEventListener('click', () => fetchData(totalPages));

    queryBtn.addEventListener('click', () => {
        fetchData(1);
    });

    tableBody.addEventListener('click', (event) => {
        if (event.target.classList.contains('details-button')) {
            const recordId = event.target.dataset.recordId;
            const record = currentRecords.get(recordId);
            
            if (record) {
                // 创建一个副本以避免修改 map 中的原始对象
                const recordToShow = { ...record };
                if (recordToShow.raw_response) {
                    delete recordToShow.raw_response;
                }
                modalData.textContent = JSON.stringify(recordToShow, null, 2);
                modal.style.display = 'block';
            }
        }
    });

    closeButton.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    });

    // --- 初始化 ---
    loadAssets();
});