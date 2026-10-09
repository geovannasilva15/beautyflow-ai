from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from html import escape
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from frontend.api_client import api_get, format_currency

TZ = ZoneInfo("America/Sao_Paulo")


def _local_date(value: str) -> date:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(TZ).date()


def _local_time(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(TZ).strftime("%H:%M")


def _calendar(year: int, month: int, appointments: list[dict], client_names: dict) -> str:
    days = calendar.Calendar(firstweekday=0).monthdatescalendar(year, month)
    today = datetime.now(TZ).date()
    by_day: dict[date, list[dict]] = {}
    for item in appointments:
        day = _local_date(item["scheduled_at"])
        by_day.setdefault(day, []).append(item)
    cells = []
    for week in days:
        for day in week:
            classes = "bf-day"
            if day.month != month:
                classes += " bf-other-month"
            if day == today:
                classes += " bf-today"
            events = []
            for appt in sorted(by_day.get(day, []), key=lambda a: a["scheduled_at"])[:3]:
                client_name = escape(str(client_names.get(appt["client_id"], "Cliente")))
                time_label = escape(_local_time(appt["scheduled_at"]))
                status = "bf-event-canceled" if appt["status"] == "canceled" else "bf-event"
                events.append(f'<div class="{status}">{time_label} · {client_name}</div>')
            extra = len(by_day.get(day, [])) - 3
            if extra > 0:
                events.append(f'<span class="bf-more">+{extra} atendimentos</span>')
            cells.append(
                f'<div class="{classes}"><span class="bf-date">{day.day}</span>{"".join(events)}</div>'
            )
    headers = "".join(f"<div class='bf-weekday'>{d}</div>" for d in ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"])
    return f'<div class="bf-calendar">{headers}{"".join(cells)}</div>'


def render() -> None:
    today = datetime.now(TZ).date()
    data = api_get("/dashboard")
    appointments = api_get("/appointments")
    clients = api_get("/clients")
    services = api_get("/services")
    professionals = api_get("/professionals")

    client_names = {c["id"]: c["name"] for c in clients}
    service_names = {s["id"]: s["name"] for s in services}
    upcoming = [
        a for a in appointments
        if a["status"] == "scheduled" and _local_date(a["scheduled_at"]) >= today
    ]
    upcoming.sort(key=lambda a: a["scheduled_at"])
    today_bookings = [a for a in upcoming if _local_date(a["scheduled_at"]) == today]
    completed_today = [
        a for a in appointments
        if a["status"] == "completed" and _local_date(a["scheduled_at"]) == today
    ]
    daily_revenue = sum(float(a.get("final_price") or 0) for a in completed_today)

    st.markdown(
        '<div class="bf-eyebrow">BEAUTYFLOW / VISÃO GERAL</div>'
        '<h1 class="bf-title">Seu negócio, em perfeita harmonia.</h1>'
        '<p class="bf-subtitle">Agenda, clientes e resultados organizados em um só lugar.</p>',
        unsafe_allow_html=True,
    )
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Agendamentos hoje", len(today_bookings))
    col2.metric("Receita realizada hoje", format_currency(daily_revenue))
    col3.metric("Profissionais ativos", len(professionals))
    col4.metric("Clientes cadastrados", data.get("total_clients", 0))

    st.write("")
    left, right = st.columns([1.9, 1], gap="large")
    with left:
        with st.container(border=True):
            header_left, header_right = st.columns([2, 1])
            with header_left:
                st.markdown("### Calendário de atendimentos")
                st.caption("Agendamentos registrados na agenda, no horário de São Paulo.")
            with header_right:
                selected = st.date_input("Escolher mês", value=today, format="DD/MM/YYYY", key="dashboard_month")
            st.markdown(_calendar(selected.year, selected.month, appointments, client_names), unsafe_allow_html=True)

    with right:
        with st.container(border=True):
            st.markdown("### Próximos atendimentos")
            st.caption("Seus próximos horários confirmados.")
            if not upcoming:
                st.info("Nenhum atendimento futuro agendado.")
            else:
                for a in upcoming[:6]:
                    label = escape(str(client_names.get(a["client_id"], "Cliente")))
                    service = escape(str(service_names.get(a["service_id"], "Serviço")))
                    when = _local_date(a["scheduled_at"]).strftime("%d/%m") + " · " + _local_time(a["scheduled_at"])
                    st.markdown(
                        f'<div class="bf-appointment"><span class="bf-appointment-time">{when}</span>'
                        f'<strong>{label}</strong><small>{service}</small></div>',
                        unsafe_allow_html=True,
                    )
        with st.container(border=True):
            st.markdown("### Acesso rápido")
            st.caption("Ações do seu dia a dia.")
            if st.button("Abrir agenda", use_container_width=True, key="dash_agenda"):
                st.session_state["bf_page"] = "Agenda"
                st.rerun()
            if st.button("Ver clientes", use_container_width=True, key="dash_clients"):
                st.session_state["bf_page"] = "Clientes"
                st.rerun()

    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("### Receita de atendimentos concluídos")
            st.metric("Acumulado", format_currency(data.get("estimated_revenue", 0)))
            st.caption("Somente serviços marcados como concluídos.")
    with c2:
        with st.container(border=True):
            st.markdown("### Ticket médio")
            st.metric("Por atendimento concluído", format_currency(data.get("average_ticket", 0)))
    with c3:
        with st.container(border=True):
            st.markdown("### Taxa de não comparecimento")
            st.metric("Sobre agendamentos registrados", f"{float(data.get('no_show_rate', 0))*100:.1f}%")

    with st.container(border=True):
        st.markdown("### Serviços mais agendados")
        top = pd.DataFrame(data.get("top_services", []))
        if top.empty:
            st.info("Os dados aparecerão após os primeiros agendamentos.")
        else:
            st.bar_chart(top.set_index("service")["count"])
