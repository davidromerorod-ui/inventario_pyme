import streamlit as st
import psycopg2
import pandas as pd

# =========================================================
# CONFIGURACIÓN DE LA PÁGINA
# =========================================================
st.set_page_config(
    page_title="PYME - Gestión de Inventario",
    page_icon="📦",
    layout="centered"
)

st.title("📦 Sistema de Inventario PYME")
st.markdown("---")


# =========================================================
# CONFIGURACIÓN DE POSTGRESQL LOCAL
# =========================================================

# =========================================================
# CONFIGURACIÓN DE POSTGRESQL: NEON Y LOCAL
# =========================================================
import os

def get_connection():
    # En Streamlit Cloud, la conexión se obtiene desde Secrets.
    try:
        database_url = st.secrets.get("DATABASE_URL")
    except Exception:
        database_url = None

    # Alternativa para variables de entorno.
    if not database_url:
        database_url = os.getenv("DATABASE_URL")

    if database_url:
        conn = psycopg2.connect(
            database_url,
            sslmode="require",
            connect_timeout=10
        )
    else:
        # Conexión local para ejecutar el proyecto en tu PC.
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="pyme_inventario_db",
            user="postgres",
            password="admin123",
            client_encoding="UTF8",
            connect_timeout=5
        )

    conn.set_client_encoding("UTF8")
    return conn

# =========================================================
# SECCIÓN 1: REGISTRAR PRODUCTOS
# =========================================================
st.header("1. Registrar Nuevo Producto")

with st.form("form_nuevo_producto", clear_on_submit=True):

    col1, col2 = st.columns(2)

    with col1:
        codigo_barras = st.text_input(
            "Código de Barras *",
            placeholder="Ej: 7701234567897"
        )

        nombre = st.text_input(
            "Nombre del Producto *",
            placeholder="Ej: Monitor LED 27"
        )

        precio_compra = st.number_input(
            "Precio Compra ($)",
            min_value=0.0,
            step=1000.0,
            value=150000.0
        )

    with col2:
        precio_venta = st.number_input(
            "Precio Venta ($) *",
            min_value=0.0,
            step=1000.0,
            value=250000.0
        )

        stock_actual = st.number_input(
            "Stock Inicial *",
            min_value=1,
            step=1,
            value=10
        )

        stock_minimo = st.number_input(
            "Stock Mínimo",
            min_value=1,
            step=1,
            value=2
        )

    id_categoria = st.number_input(
        "ID Categoría",
        min_value=1,
        step=1,
        value=1
    )

    submitted = st.form_submit_button("🚀 Guardar Producto")


if submitted:

    if not codigo_barras.strip() or not nombre.strip():
        st.error("El código de barras y el nombre son obligatorios.")

    else:
        conn = None

        try:
            conn = get_connection()

            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO producto (
                        codigo_barras,
                        nombre,
                        precio_compra,
                        precio_venta,
                        stock_actual,
                        stock_minimo,
                        id_categoria
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        codigo_barras.strip(),
                        nombre.strip(),
                        precio_compra,
                        precio_venta,
                        stock_actual,
                        stock_minimo,
                        id_categoria
                    )
                )

            conn.commit()

            st.success(
                f"Producto '{nombre}' registrado correctamente."
            )

            st.rerun()

        except Exception as e:
            if conn is not None:
                conn.rollback()

            st.error(f"Error al registrar el producto: {e}")

        finally:
            if conn is not None:
                conn.close()


st.markdown("---")


# =========================================================
# SECCIÓN 2: PROBAR LA CONEXIÓN
# =========================================================
st.header("2. Estado de la Base de Datos")

if st.button("🔎 Comprobar conexión"):

    conn = None

    try:
        conn = get_connection()
        st.success("Conexión con PostgreSQL establecida.")

        with conn.cursor() as cur:
            cur.execute("SHOW server_encoding;")
            server_encoding = cur.fetchone()[0]

            cur.execute("SHOW client_encoding;")
            client_encoding = cur.fetchone()[0]

            cur.execute("SELECT 1;")
            prueba = cur.fetchone()[0]

        st.write("Codificación del servidor:", server_encoding)
        st.write("Codificación del cliente:", client_encoding)
        st.write("Prueba SQL:", prueba)

    except Exception as e:
        st.error(f"Error de conexión o consulta: {e}")

    finally:
        if conn is not None:
            conn.close()


st.markdown("---")


# =========================================================
# SECCIÓN 3: CONSULTAR PRODUCTOS
# =========================================================
st.header("3. Productos en la Base de Datos")

if st.button("🔄 Actualizar Tabla de Productos"):
    st.rerun()

conn = None

try:
    conn = get_connection()

    query = """
        SELECT
            id_producto AS "ID",
            codigo_barras AS "Código",
            nombre AS "Nombre",
            precio_venta AS "Precio Venta",
            stock_actual AS "Stock"
        FROM producto
        ORDER BY id_producto DESC;
    """

    df = pd.read_sql_query(query, conn)

    if not df.empty:
        st.dataframe(df, use_container_width=True)
        st.caption(f"Total de productos: {len(df)}")

    else:
        st.info("No hay productos registrados todavía.")

except Exception as e:
    st.error(f"Error al cargar la tabla: {e}")

finally:
    if conn is not None:
        conn.close()
