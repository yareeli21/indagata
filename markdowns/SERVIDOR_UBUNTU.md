# Montar Indagata en el servidor Ubuntu

Servidor con Docker, una GPU NVIDIA, Ollama instalado como servicio del sistema y Caddy en los puertos 80/443.
El proyecto usa `docker-compose.yml` más `docker-compose.servidor.yml` (usa el Ollama de la máquina, fija
ChromaDB 1.4.4 y publica los puertos solo en `127.0.0.1`).

## 1. Código y archivos migrados

```bash
cd ~ && git clone -b PArturo https://github.com/yareeli21/indagata.git
# ~/migracion_indagata: indagata_db.dump, chromadb_data.tgz, storage.tgz, env_indagata.txt
cd ~/indagata
cp ~/migracion_indagata/env_indagata.txt .env
tar xzf ~/migracion_indagata/storage.tgz
```

En `.env`: `OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M` y `RAG_JUEZ_MODELO=llama3.1:8b-instruct-q4_K_M`
(el juez local por omisión, qwen2.5:3b, no está instalado en el servidor).

## 2. Ollama accesible para los contenedores

Ollama escucha en `127.0.0.1`; los contenedores llegan por la red de Docker, así que debe escuchar en todas las
interfaces, y el firewall impide entrar a ese puerto desde fuera:

```bash
sudo systemctl edit ollama      # agregar:  [Service]  Environment="OLLAMA_HOST=0.0.0.0:11434"
sudo systemctl restart ollama
sudo ufw allow from 172.16.0.0/12 to any port 11434 proto tcp   # redes de Docker
sudo ufw deny 11434/tcp
```

## 3. Datos

```bash
docker compose -f docker-compose.yml -f docker-compose.servidor.yml up -d postgres chromadb
docker compose -f docker-compose.yml -f docker-compose.servidor.yml stop chromadb
docker run --rm -v indagata_chromadb_data:/datos -v ~/migracion_indagata:/respaldo alpine \
  sh -c "rm -rf /datos/* && tar xzf /respaldo/chromadb_data.tgz -C /datos"
docker compose cp ~/migracion_indagata/indagata_db.dump postgres:/tmp/indagata_db.dump
docker compose exec postgres pg_restore -U postgres -d indagata_db --clean --if-exists /tmp/indagata_db.dump
# El respaldo es anterior a la gestión de usuarios: aplicar su migración después de restaurar.
docker compose exec postgres psql -U postgres -d indagata_db -f /migrations/2026_22_usuarios_gestion.sql
```

## 4. Levantar

```bash
docker compose -f docker-compose.yml -f docker-compose.servidor.yml up -d --build
```

## 5. Publicar en internet (Caddy)

Antes: cambiar `SECRET_KEY`, `POSTGRES_PASSWORD` y las contraseñas de los usuarios de prueba. Solo la página y la
API se publican por Caddy con HTTPS; la base de datos, Chroma, Redis y Ollama nunca.
