# **Neo - Backend**

助力mRNA疫苗研发的AI模型的后端

基于前沿AI算法，助力mRNA疫苗研发，迈向自动化和智能化时代，端到端mRNA研发解决方案，加速疫苗与治疗创新

地址：https://www.mrnaneo.com

## 

### 前提条件

- 建议Python 3.10

### 安装步骤

1. **克隆仓库**

```bash
git clone -b backend https://github.com/Morpheusai/Molly.git
cd Molly
```

2. **安装依赖**

```bash
pip install -r requirements.txt
```

3. **配置环境变量** 

   创建 `.env` 文件并配置以下内容：

```bash
# 数据库配置
DB_HOST="Your DB_HOST"
DB_PORT="Your DB_PORT"
DB_USER="Your DB_USER"
DB_PASSWORD="Your DB_PASSWORD"
DB_NAME="Your DB_NAME"
#微信开放平台应用的 AppID 和 AppSecret
WECHAT_APP_ID="Your WECHAT_APP_ID"
WECHAT_APP_SECRET="Your WECHAT_APP_SECRET"
M_WECHAT_APP_ID="Your M_WECHAT_APP_ID"
M_WECHAT_APP_SECRET="Your M_WECHAT_APP_SECRET"
# JWT 配置
SECRET_KEY="Your SECRET_KEY"
ALGORITHM="Your ALGORITHM"
ACCESS_TOKEN_EXPIRE_MINUTES="Your ACCESS_TOKEN_EXPIRE_MINUTES"
#minio配置
MINIO_SERVER="Your MINIO_SERVER"
MINIO_ACCESS_KEY="Your MINIO_ACCESS_KEY"
MINIO_SECRET_KEY="Your MINIO_SECRET_KEY"
MINIO_SECURE="Your MINIO_SECURE"
MINIO_BUCKET_MOLLY="Your MINIO_BUCKET_MOLLY"
MINIO_BUCKET_NETMHCPAN_RESULTS="Your MINIO_BUCKET_NETMHCPAN_RESULTS"
MINIO_BUCKET_WEBLOGO="Your MINIO_BUCKET_WEBLOGO"

```

4. **启动项目**

```bash
./run.sh
```

