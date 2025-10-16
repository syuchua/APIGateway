# uv环境配置
# API Gateway项目使用uv管理Python环境

# 创建虚拟环境
uv venv

# 激活环境 (Windows)
.venv\Scripts\activate

# 激活环境 (Linux/Mac)
source .venv/bin/activate

# 安装项目依赖
uv pip install -e .

# 安装开发依赖
uv pip install -e ".[dev]"

# 安装测试依赖
uv pip install -e ".[test]"

# 运行测试
uv run pytest

# 运行应用
uv run python -m app.main

# 代码格式化
uv run black .
uv run isort .

# 类型检查
uv run mypy app/

# 更新依赖
uv pip compile pyproject.toml

# 同步依赖
uv pip sync