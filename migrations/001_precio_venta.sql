-- Migración 001 — Estructura de precio en productos
-- Feature: modulo-chofer-precios
--
-- Qué hace:
--   - renombra productos.precio_unitario -> productos.precio_venta (conserva datos)
--   - agrega productos.precio_compra (costo pyme, default 0)
--   - agrega productos.ganancia (margen admin, default 0)
--
-- OJO: precio_unitario en movimientos/rendiciones/facturas es transaccional,
-- NO se toca. Esta migración solo afecta la tabla productos (catálogo).
--
-- Cómo correr en Neon: SQL Editor -> pegar cada bloque -> ejecutar.
-- Correr PRIMERO en la rama QA. Verificar. Recién ahí en producción.


-- ============================================================
-- PASO 0 — Estado ANTES (debe aparecer precio_unitario)
-- ============================================================
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'productos';


-- ============================================================
-- PASO 1 — Migración (todo o nada: si falla, no queda a medias)
-- ============================================================
BEGIN;

ALTER TABLE productos RENAME COLUMN precio_unitario TO precio_venta;

ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS precio_compra NUMERIC(10,2) NOT NULL DEFAULT 0;

ALTER TABLE productos
    ADD COLUMN IF NOT EXISTS ganancia NUMERIC(10,2) NOT NULL DEFAULT 0;

COMMIT;


-- ============================================================
-- PASO 2 — Verificación (correr después del COMMIT)
-- ============================================================

-- Chequeo 1: columnas correctas.
-- Esperado: aparecen precio_venta, precio_compra, ganancia.
--           NO aparece precio_unitario.
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'productos';

-- Chequeo 2: datos intactos.
-- Esperado: precio_venta conserva los precios de siempre;
--           precio_compra y ganancia en 0; ninguna fila perdida.
SELECT formato, precio_venta, precio_compra, ganancia
FROM productos
ORDER BY formato;

-- Chequeo 3 (fuera de SQL): levantar QA, login admin, GET /productos/
-- Si devuelve los 3 campos sin error 500 -> esquema y código coinciden.
