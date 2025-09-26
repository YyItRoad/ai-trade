document.addEventListener('DOMContentLoaded', () => {
    const apiKeyInput = document.getElementById('api-key-input');
    const saveKeyBtn = document.getElementById('save-key-btn');
    const statusMessage = document.getElementById('login-status-message');
    
    const STORAGE_KEY = 'app_config_key';

    // 检查密钥是否已存在。如果存在，则重定向到主页。
    if (localStorage.getItem(STORAGE_KEY)) {
        window.location.href = '/';
        return; // 停止后续执行
    }

    saveKeyBtn.addEventListener('click', async () => {
        const key = apiKeyInput.value.trim();

        if (!key) {
            statusMessage.textContent = '密钥不能为空。';
            statusMessage.style.color = 'red';
            return;
        }

        statusMessage.textContent = '正在验证密钥...';
        statusMessage.style.color = 'inherit';
        saveKeyBtn.disabled = true;

        try {
            const response = await fetch('/api/verify-key', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ key: key }),
            });

            if (response.ok) {
                // 密钥有效，保存并重定向
                localStorage.setItem(STORAGE_KEY, key);
                statusMessage.textContent = '验证成功！正在跳转...';
                statusMessage.style.color = 'green';
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            } else {
                // 密钥无效
                const errorData = await response.json();
                statusMessage.textContent = `错误: ${errorData.detail || '密钥无效'}`;
                statusMessage.style.color = 'red';
            }
        } catch (error) {
            statusMessage.textContent = '网络错误或服务器无法连接。';
            statusMessage.style.color = 'red';
            console.error('验证密钥时出错:', error);
        } finally {
            saveKeyBtn.disabled = false;
        }
    });
});