document.addEventListener('DOMContentLoaded', () => {
    // --- 身份验证检查 ---
    if (!localStorage.getItem('app_config_key')) {
        window.location.href = '/login';
        return;
    }

    // --- DOM 元素 ---
    const tableBody = document.getElementById('assets-table-body');
    const addAssetBtn = document.getElementById('add-asset-btn');
    const assetModal = document.getElementById('asset-modal');
    const closeModalBtn = assetModal.querySelector('.close-button');
    const assetForm = document.getElementById('asset-form');
    const modalTitle = document.getElementById('modal-title');
    const assetIdInput = document.getElementById('asset-id');
    const assetSymbolInput = document.getElementById('asset-symbol');
    const assetTypeSelect = document.getElementById('asset-type'); // 新增
    const statusMessage = document.getElementById('asset-status-message');

    let allAssets = []; // 用于存储所有资产数据
    const assetTypeMap = { // 用于显示资产类型
        0: '现货',
        1: 'U本位',
        2: '币本位'
    };

    // --- API 调用函数 ---
    async function fetchAssets() {
        try {
            const response = await fetch('/api/assets');
            if (!response.ok) throw new Error('获取资产列表失败');
            allAssets = await response.json();
            renderTable();
        } catch (error) {
            console.error('Error fetching assets:', error);
            alert(error.message);
            tableBody.innerHTML = '<tr><td colspan="3">加载资产失败。</td></tr>';
        }
    }

    async function saveAsset(assetData) {
        const method = assetData.id ? 'PUT' : 'POST';
        const url = assetData.id ? `/api/assets/${assetData.id}` : '/api/assets';
        try {
            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(assetData)
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '保存资产失败');
            }
            statusMessage.textContent = '保存成功！';
            statusMessage.style.color = 'green';
            await fetchAssets(); // 重新加载资产列表
            setTimeout(closeModal, 1000);
        } catch (error) {
            statusMessage.textContent = `错误: ${error.message}`;
            statusMessage.style.color = 'red';
        }
    }

    async function deleteAsset(id) {
        try {
            const response = await fetch(`/api/assets/${id}`, { method: 'DELETE' });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '删除资产失败');
            }
            await fetchAssets(); // 重新加载资产列表
        } catch (error) {
            alert(`删除错误: ${error.message}`);
        }
    }

    // --- 渲染函数 ---
    function renderTable() {
        tableBody.innerHTML = '';
        if (allAssets.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4">未找到任何资产。</td></tr>';
            return;
        }
        allAssets.forEach(asset => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${asset.id}</td>
                <td>${asset.symbol}</td>
                <td>${assetTypeMap[asset.type] || '未知'}</td>
                <td>
                    <button class="edit-asset-btn" data-id="${asset.id}">编辑</button>
                    <button class="delete-asset-btn" data-id="${asset.id}">删除</button>
                </td>
            `;
            tableBody.appendChild(row);
        });
    }

    // --- 模态框控制 ---
    function openModal(asset = null) {
        assetForm.reset();
        statusMessage.textContent = '';
        if (asset) {
            modalTitle.textContent = '编辑资产';
            assetIdInput.value = asset.id;
            assetSymbolInput.value = asset.symbol;
            assetTypeSelect.value = asset.type; // 设置资产类型
        } else {
            modalTitle.textContent = '添加新资产';
            assetIdInput.value = '';
            assetTypeSelect.value = '0'; // 默认选择现货
        }
        assetModal.style.display = 'block';
    }

    function closeModal() {
        assetModal.style.display = 'none';
    }

    // --- 事件监听器 ---
    addAssetBtn.addEventListener('click', () => openModal());
    closeModalBtn.addEventListener('click', closeModal);
    window.addEventListener('click', (event) => {
        if (event.target === assetModal) closeModal();
    });

    assetForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const assetData = {
            id: assetIdInput.value ? parseInt(assetIdInput.value) : null,
            symbol: assetSymbolInput.value.trim(),
            type: parseInt(assetTypeSelect.value) // 获取资产类型
        };
        await saveAsset(assetData);
    });

    tableBody.addEventListener('click', (event) => {
        const target = event.target;
        const assetId = target.dataset.id;

        if (target.classList.contains('edit-asset-btn')) {
            const asset = allAssets.find(a => a.id == assetId);
            if (asset) openModal(asset);
        }

        if (target.classList.contains('delete-asset-btn')) {
            if (confirm(`确定要删除资产 ID: ${assetId} (${allAssets.find(a => a.id == assetId).symbol}) 吗?`)) {
                deleteAsset(assetId);
            }
        }
    });

    // --- 初始化 ---
    fetchAssets();
});