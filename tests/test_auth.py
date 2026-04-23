import sys
sys.path.insert(0, '.')

import pytest
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────

@pytest.fixture
def mock_streamlit():
    """Mock completo de streamlit para evitar errores de contexto."""
    with patch("app.auth.st") as mock_st:
        mock_st.session_state = {}
        mock_st.secrets = {
            "LOGIN_USER":     "admin",
            "LOGIN_PASSWORD": "secreto123",
        }
        mock_st.form.return_value.__enter__ = MagicMock(return_value=None)
        mock_st.form.return_value.__exit__  = MagicMock(return_value=False)
        yield mock_st


# ─────────────────────────────────────────
# TESTS
# ─────────────────────────────────────────

def test_ya_autenticado(mock_streamlit):
    """Si session_state tiene authenticated=True, retorna True sin pedir login."""
    from app.auth import check_password
    mock_streamlit.session_state["authenticated"] = True
    result = check_password()
    assert result is True
    mock_streamlit.form.assert_not_called()


def test_credenciales_correctas(mock_streamlit):
    """Credenciales correctas deben setear authenticated=True y hacer rerun."""
    from app.auth import check_password

    mock_streamlit.session_state = {}

    # Simular submit del form
    mock_streamlit.text_input.side_effect = ["admin", "secreto123"]
    mock_streamlit.form_submit_button = MagicMock(return_value=True)

    # stop() lanza excepción en Streamlit real — la simulamos
    mock_streamlit.stop.side_effect = Exception("st.stop called")

    with pytest.raises(Exception, match="st.stop called"):
        check_password()

    # Aunque stop fue llamado, authenticated debería estar seteado
    # antes del rerun si las credenciales son correctas
    mock_streamlit.rerun.assert_called_once()


def test_credenciales_incorrectas(mock_streamlit):
    """Credenciales incorrectas deben mostrar error y no autenticar."""
    from app.auth import check_password

    mock_streamlit.session_state = {}
    mock_streamlit.text_input.side_effect = ["admin", "password_malo"]
    mock_streamlit.form_submit_button = MagicMock(return_value=True)
    mock_streamlit.stop.side_effect = Exception("st.stop called")

    with pytest.raises(Exception, match="st.stop called"):
        check_password()

    assert not mock_streamlit.session_state.get("authenticated")
    mock_streamlit.error.assert_called_once_with("Usuario o contraseña incorrectos")


def test_sin_submit_no_autentica(mock_streamlit):
    """Sin hacer submit, no debe autenticar."""
    from app.auth import check_password

    mock_streamlit.session_state = {}
    mock_streamlit.form_submit_button = MagicMock(return_value=False)
    mock_streamlit.stop.side_effect = Exception("st.stop called")

    with pytest.raises(Exception, match="st.stop called"):
        check_password()

    assert not mock_streamlit.session_state.get("authenticated")
    mock_streamlit.error.assert_not_called()


def test_usuario_vacio_no_autentica(mock_streamlit):
    """Usuario vacío no debe autenticar aunque password sea correcto."""
    from app.auth import check_password

    mock_streamlit.session_state = {}
    mock_streamlit.text_input.side_effect = ["", "secreto123"]
    mock_streamlit.form_submit_button = MagicMock(return_value=True)
    mock_streamlit.stop.side_effect = Exception("st.stop called")

    with pytest.raises(Exception, match="st.stop called"):
        check_password()

    assert not mock_streamlit.session_state.get("authenticated")
    mock_streamlit.error.assert_called_once()
