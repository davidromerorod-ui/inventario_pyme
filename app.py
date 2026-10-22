import os
import pandas as pd
import psycopg2
import streamlit as st

# =========================================================
# CONFIGURACIÓN DE LA PÁGINA
# =========================================================
st.set_page_config(
    page_title="PYME - Sistema Seguro de Inventario",
    page_icon="🛡️",
    layout="wide",
)


# =========================================================
# CONFIGURACIÓN DE CONEXIÓN A POSTGRESQL (NEON / LOCAL)
# =========================================================
def get_connection():
    # Intenta obtener la URL desde Streamlit Secrets (Cloud / Neon)
    try:
        database_url = st.secrets.get("DATABASE_URL")
    except Exception:
        database_url = None

    # Alternativa desde variable de entorno
    if not database_url:
        database_url = os.getenv("DATABASE_URL")

    if database_url:
        conn = psycopg2.connect(
            database_url, sslmode="require", connect_timeout=10
        )
    else:
        # Fallback para conexión local
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            dbname="pyme_inventario_db",
            user="postgres",
            password="admin123",
            client_encoding="UTF8",
            connect_timeout=5,
        )

    conn.set_client_encoding("UTF8")
    return conn


# =========================================================
# GESTIÓN DE SESIÓN Y AUTENTICACIÓN (RBAC)
# =========================================================
if "usuario_logged" not in st.session_state:
    st.session_state.usuario_logged = None
    st.session_state.rol_logged = None
    st.session_state.nombre_empleado = None


def validar_login(usuario, password):
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            # Consulta sanitizada (Prevención SQL Injection)
            query = """
                SELECT u.Username, u.Rol, e.Nombre 
                FROM Usuario u
                JOIN Empleado e ON u.Empleado_idEmpleado = e.idEmpleado
                WHERE u.Username = %s AND u.PasswordHash = %s;
            """
            cur.execute(query, (usuario, password))
            user = cur.fetchone()
        conn.close()
        return user
    except Exception as e:
        st.error(f"Error en autenticación: {e}")
        return None


# PANTALLA DE LOGIN
if st.session_state.usuario_logged is None:
    st.title("🛡️ Sistema de Inventario PYME - Inicio de Sesión")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            st.subheader("Acceso Basado en Roles (RBAC)")
            user_input = st.text_input("Usuario")
            pass_input = st.text_input("Contraseña", type="password")
            btn_login = st.form_submit_button("Iniciar Sesión")

            if btn_login:
                datos = validar_login(user_input.strip(), pass_input.strip())
                if datos:
                    st.session_state.usuario_logged = datos[0]
                    st.session_state.rol_logged = datos[1]
                    st.session_state.nombre_empleado = datos[2]
                    st.success(f"Bienvenido/a {datos[2]}")
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")
    st.stop()


# =========================================================
# BARRA LATERAL (INFORMACIÓN DE USUARIO Y LOGOUT)
# =========================================================
st.sidebar.title(f"👤 {st.session_state.nombre_empleado}")
st.sidebar.write(f"**Usuario:** `{st.session_state.usuario_logged}`")
st.sidebar.info(f"**Rol:** {st.session_state.rol_logged}")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.usuario_logged = None
    st.session_state.rol_logged = None
    st.session_state.nombre_empleado = None
    st.rerun()

st.title("📦 Panel General de Operaciones")
st.markdown("---")


# =========================================================
# ESTRUCTURA DE PESTAÑAS SEGÚN ROL
# =========================================================
if st.session_state.rol_logged == "Admin":
    tab_prod, tab_emp, tab_cat = st.tabs(
        [
            "📦 Productos (Full CRUD)",
            "👥 Gestión de Empleados",
            "🏷️ Categorías",
        ]
    )
else:
    tab_prod, tab_emp, tab_cat = st.tabs(
        [
            "📦 Inventario (Consulta)",
            "👥 Directorio de Empleados",
            "🏷️ Categorías",
        ]
    )


# =========================================================
# 1. MÓDULO DE PRODUCTOS
# =========================================================
with tab_prod:
    st.header("1. Inventario de Productos")

    # READ: Todos los roles pueden consultar
    try:
        conn = get_connection()
        query = """
            SELECT 
                p.idproducto AS "ID", 
                p.Codigo_barras AS "Código", 
                p.Nombre AS "Producto", 
                c.Nombre AS "Categoría",
                p.Precio_compra AS "P. Compra",
                p.Precio_venta AS "P. Venta", 
                p.Stock_actual AS "Stock" 
            FROM Producto p
            LEFT JOIN Categoria c ON p.idCategoria = c.idCategoria
            ORDER BY p.idproducto DESC;
        """
        df_prod = pd.read_sql_query(query, conn)
        conn.close()

        if not df_prod.empty:
            st.dataframe(df_prod, use_container_width=True)
            st.caption(f"Total de productos: {len(df_prod)}")
        else:
            st.info("No hay productos registrados en el sistema.")
    except Exception as e:
        st.error(f"Error al cargar productos: {e}")

    # OPERACIONES ESCRITURA: Solo para Administradores
    if st.session_state.rol_logged == "Admin":
        st.markdown("---")
        st.subheader("🛠️ Acciones Administrativas sobre Productos")

        tab_crear, tab_editar, tab_borrar = st.tabs(
            ["➕ Crear", "✏️ Modificar", "🗑️ Eliminar"]
        )

        with tab_crear:
            with st.form("form_crear_producto", clear_on_submit=True):
                c1, c2 = st.columns(2)
                with c1:
                    cod = st.text_input("Código de Barras *")
                    nom = st.text_input("Nombre del Producto *")
                    p_compra = st.number_input(
                        "Precio Compra ($)", min_value=0.0, step=1000.0
                    )
                with c2:
                    p_venta = st.number_input(
                        "Precio Venta ($) *", min_value=0.0, step=1000.0
                    )
                    stk = st.number_input(
                        "Stock Inicial *", min_value=1, step=1, value=10
                    )
                    cat_id = st.number_input(
                        "ID Categoría *", min_value=1, step=1, value=1
                    )

                btn_guardar = st.form_submit_button("Registrar Producto")

                if btn_guardar:
                    if not cod.strip() or not nom.strip():
                        st.error("Código y Nombre son campos obligatorios.")
                    else:
                        try:
                            conn = get_connection()
                            with conn.cursor() as cur:
                                cur.execute(
                                    """
                                    INSERT INTO Producto (Codigo_barras, Nombre, Precio_compra, Precio_venta, Stock_actual, idCategoria)
                                    VALUES (%s, %s, %s, %s, %s, %s);
                                    """,
                                    (
                                        cod.strip(),
                                        nom.strip(),
                                        p_compra,
                                        p_venta,
                                        stk,
                                        cat_id,
                                    ),
                                )
                            conn.commit()
                            conn.close()
                            st.success(
                                f"Producto '{nom}' creado correctamente."
                            )
                            st.rerun()
                        except Exception as ex:
                            st.error(f"Error al guardar: {ex}")

        with tab_editar:
            with st.form("form_editar_producto"):
                id_mod = st.number_input(
                    "ID del Producto a Modificar", min_value=1, step=1
                )
                nuevo_p_venta = st.number_input(
                    "Nuevo Precio Venta ($)", min_value=0.0, step=1000.0
                )
                nuevo_stock = st.number_input(
                    "Nuevo Stock Actual", min_value=0, step=1
                )
                btn_actualizar = st.form_submit_button("Actualizar Datos")

                if btn_actualizar:
                    try:
                        conn = get_connection()
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                UPDATE Producto 
                                SET Precio_venta = %s, Stock_actual = %s 
                                WHERE idproducto = %s;
                                """,
                                (nuevo_p_venta, nuevo_stock, id_mod),
                            )
                        conn.commit()
                        conn.close()
                        st.success(f"Producto ID {id_mod} actualizado.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error al actualizar: {ex}")

        with tab_borrar:
            with st.form("form_eliminar_producto"):
                id_del = st.number_input(
                    "ID del Producto a Eliminar", min_value=1, step=1
                )
                btn_eliminar = st.form_submit_button(
                    "🚨 Confirmar Eliminación"
                )

                if btn_eliminar:
                    try:
                        conn = get_connection()
                        with conn.cursor() as cur:
                            cur.execute(
                                "DELETE FROM Producto WHERE idproducto = %s;",
                                (id_del,),
                            )
                        conn.commit()
                        conn.close()
                        st.warning(f"Producto ID {id_del} eliminado.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error al eliminar: {ex}")


# =========================================================
# 2. MÓDULO DE EMPLEADOS
# =========================================================
with tab_emp:
    st.header("2. Gestión de Empleados")

    try:
        conn = get_connection()
        df_emp = pd.read_sql_query(
            """
            SELECT 
                idEmpleado AS "ID", 
                Identificacion AS "Cédula", 
                Nombre AS "Empleado", 
                Cargo AS "Cargo", 
                Telefono AS "Teléfono",
                Empleadocol AS "Sede"
            FROM Empleado 
            ORDER BY idEmpleado DESC;
            """,
            conn,
        )
        conn.close()
        st.dataframe(df_emp, use_container_width=True)
    except Exception as e:
        st.error(f"Error al consultar empleados: {e}")

    if st.session_state.rol_logged == "Admin":
        st.markdown("---")
        st.subheader("➕ Registrar Nuevo Empleado")
        with st.form("form_nuevo_empleado", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                emp_ident = st.text_input("Identificación / Cédula *")
                emp_nom = st.text_input("Nombre Completo *")
                emp_cargo = st.selectbox(
                    "Cargo",
                    [
                        "Gerente General",
                        "Vendedor de Tecnología",
                        "Soporte Técnico",
                        "Administrador",
                    ],
                )
            with col2:
                emp_tel = st.text_input("Teléfono", value="3000000000")
                emp_sede = st.text_input("Sede", value="Sede Principal")

            btn_emp = st.form_submit_button("Guardar Empleado")

            if btn_emp:
                if not emp_ident.strip() or not emp_nom.strip():
                    st.error("Cédula y Nombre son obligatorios.")
                else:
                    try:
                        conn = get_connection()
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                INSERT INTO Empleado (Identificacion, Nombre, Cargo, Telefono, Empleadocol)
                                VALUES (%s, %s, %s, %s, %s);
                                """,
                                (
                                    emp_ident.strip(),
                                    emp_nom.strip(),
                                    emp_cargo,
                                    emp_tel.strip(),
                                    emp_sede.strip(),
                                ),
                            )
                        conn.commit()
                        conn.close()
                        st.success("Empleado registrado con éxito.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Error al guardar empleado: {ex}")


# =========================================================
# 3. MÓDULO DE CATEGORÍAS
# =========================================================
with tab_cat:
    st.header("3. Categorías de Productos")

    try:
        conn = get_connection()
        df_cat = pd.read_sql_query(
            """
            SELECT 
                idCategoria AS "ID", 
                Nombre AS "Categoría", 
                Descripcion AS "Descripción"
            FROM Categoria 
            ORDER BY idCategoria ASC;
            """,
            conn,
        )
        conn.close()
        st.dataframe(df_cat, use_container_width=True)
    except Exception as e:
        st.error(f"Error al cargar categorías: {e}")
