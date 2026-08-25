# 🧭 Pusula — Dış Ticaret İstihbarat Platformu

Bu proje, ihracat yapan firmaların hedef pazarlardaki potansiyel alıcıları bulmasını kolaylaştırmak için geliştirilmiş bir **Dış Ticaret İstihbarat ve Müşteri Bulma Platformudur**.

## 🚀 Kurulum ve Çalıştırma

### 1. Bağımlılıkları Yükleyin

```bash
cd backend
python -m venv venv

# Windows:
venv\Scripts\activate

# Linux / Mac:
# source venv/bin/activate

pip install -r requirements.txt
```

### 2. Ayarları Yapın ve Veritabanını Hazırlayın

`backend/.env.example` dosyasını `backend/.env` olarak kopyalayın:

```bash
cp .env.example .env
alembic upgrade head
```

### 3. Sunucuyu Başlatın

```bash
python run.py
```

Tarayıcınızdan **`http://127.0.0.1:5000`** adresini açarak uygulamayı kullanabilirsiniz.

---

## 🐳 Docker ile Çalıştırma

```bash
docker build -t pusula -f backend/Dockerfile .
docker run -p 5000:5000 --env-file backend/.env pusula
```

---
