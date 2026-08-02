@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo.
echo  ============================
echo   TuneBox 一键启动
echo  ============================
echo.

where uv >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 uv，请先安装: https://docs.astral.sh/uv/
    pause
    exit /b 1
)

echo [1/4] 检查后端依赖...
if not exist ".venv\Scripts\python.exe" (
    echo        首次运行，安装后端依赖...
    uv sync
    if errorlevel 1 (
        echo [错误] 后端依赖安装失败
        pause
        exit /b 1
    )
) else (
    echo        已就绪
)

echo [2/4] 检查前端依赖...
where pnpm >nul 2>nul
if errorlevel 1 (
    echo [错误] 未找到 pnpm，请先安装: npm install -g pnpm
    pause
    exit /b 1
)
if not exist "frontend\node_modules" (
    echo        首次运行，安装前端依赖...
    pushd frontend
    call pnpm install
    if errorlevel 1 (
        echo [错误] 前端依赖安装失败
        popd
        pause
        exit /b 1
    )
    popd
) else (
    echo        已就绪
)

echo [3/4] 构建前端...
pushd frontend
call pnpm build
if errorlevel 1 (
    echo [错误] 前端构建失败
    popd
    pause
    exit /b 1
)
popd

echo [4/4] 启动服务（默认 HTTPS 端口 2053，可用 --port 指定）...
echo        Ctrl+C 停止
echo.
pushd backend
call uv run music-server %*
popd

pause
