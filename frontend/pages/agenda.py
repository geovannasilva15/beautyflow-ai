from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from frontend.api_client import BeautyFlowAPIError, api_get, api_patch, api_post, format_currency
from frontend.pages.dashboard import _calendar, _local_date, _local_time

TZ = ZoneInfo('America/Sao_Paulo')

STATUS_OPTIONS = {
    "Agendado": "scheduled",
    "Concluído": "completed",
    "Cancelado": "canceled",
    "Não compareceu": "no_show",
}

STATUS_LABELS = {value: label for label, value in STATUS_OPTIONS.items()}


def render() -> None:
    st.markdown('<div class="bf-eyebrow">BEAUTYFLOW / AGENDA</div><h1 class="bf-title">Sua agenda, no seu ritmo.</h1><p class="bf-subtitle">Organize atendimentos e encontre horários livres.</p>', unsafe_allow_html=True)

    clients = api_get("/clients")
    services = api_get("/services")
    professionals = api_get("/professionals")
    appointments = api_get("/appointments")

    client_map = {f"{item['name']} · ID {item['id']}": item for item in clients}
    service_map = {f"{item['name']} · {format_currency(item['price'])}": item for item in services}
    professional_map = {f"{item['name']} · {item['specialty']}": item for item in professionals}

    with st.container(border=True):
        st.markdown("### Novo agendamento")
        if not clients or not services or not professionals:
            st.warning("Cadastre pelo menos um cliente, um serviço e um profissional antes de criar agendamentos.")
        else:
            with st.form("appointment_create", clear_on_submit=False):
                c1, c2, c3 = st.columns(3)
                selected_client = c1.selectbox("Cliente", list(client_map.keys()))
                selected_service = c2.selectbox("Serviço", list(service_map.keys()))
                selected_professional = c3.selectbox("Profissional", list(professional_map.keys()))
                scheduled_date = c1.date_input("Data", value=datetime.now(TZ).date() + timedelta(days=1))
                scheduled_time = c2.time_input("Horário", value=time(14, 0))
                final_price = c3.number_input(
                    "Preço final",
                    min_value=0.0,
                    value=float(service_map[selected_service]["price"]),
                    step=10.0,
                )
                notes = st.text_area("Observações", placeholder="Ex: cliente prefere atendimento pela manhã")

                if st.form_submit_button("Criar agendamento"):
                    try:
                        api_post(
                            "/appointments",
                            json={
                                "client_id": client_map[selected_client]["id"],
                                "service_id": service_map[selected_service]["id"],
                                "professional_id": professional_map[selected_professional]["id"],
                                "scheduled_at": datetime.combine(scheduled_date, scheduled_time).isoformat(),
                                "final_price": float(final_price),
                                "notes": notes or None,
                            },
                        )
                    except BeautyFlowAPIError as exc:
                        st.error(str(exc))
                    else:
                        st.success("Agendamento criado com sucesso.")
                        st.rerun()

            selected_service_data = service_map[selected_service]
            selected_professional_data = professional_map[selected_professional]
            try:
                availability = api_get(
                    "/appointments/availability",
                    params={
                        "professional_id": selected_professional_data["id"],
                        "service_id": selected_service_data["id"],
                        "target_date": scheduled_date.isoformat(),
                    },
                )
                slots = availability.get("slots", [])
                if slots:
                    labels = [datetime.fromisoformat(slot).strftime("%H:%M") for slot in slots[:12]]
                    st.caption("Horários livres nessa data: " + " · ".join(labels))
                else:
                    st.caption("Nenhum horário livre encontrado para essa combinação.")
            except BeautyFlowAPIError as exc:
                st.warning(f"Não foi possível consultar horários livres: {exc}")

    st.markdown("### Visão da agenda")
    with st.container(border=True):
        calendar_date = st.date_input("Selecionar mês", value=datetime.now(TZ).date(), format="DD/MM/YYYY", key="agenda_calendar_month")
        st.markdown(_calendar(calendar_date.year, calendar_date.month, appointments, {c["id"]: c["name"] for c in clients}), unsafe_allow_html=True)

    st.markdown("### Agendamentos")
    appointment_df = pd.DataFrame(appointments)
    if appointment_df.empty:
        st.info("Nenhum agendamento encontrado.")
        return

    clients_by_id = {item["id"]: item["name"] for item in clients}
    services_by_id = {item["id"]: item["name"] for item in services}
    professionals_by_id = {item["id"]: item["name"] for item in professionals}

    appointment_df["cliente"] = appointment_df["client_id"].map(clients_by_id)
    appointment_df["serviço"] = appointment_df["service_id"].map(services_by_id)
    appointment_df["profissional"] = appointment_df["professional_id"].map(professionals_by_id)
    appointment_df["status_nome"] = appointment_df["status"].map(STATUS_LABELS).fillna(appointment_df["status"])
    appointment_df["valor"] = appointment_df["final_price"].apply(format_currency)

    appointment_df["data_local"] = appointment_df["scheduled_at"].map(_local_date)
    appointment_df["Data"] = appointment_df["data_local"].map(lambda d: d.strftime("%d/%m/%Y"))
    appointment_df["Horário"] = appointment_df["scheduled_at"].map(_local_time)
    with st.container(border=True):
        filter_col, status_col = st.columns(2)
        day = filter_col.date_input("Dia", value=datetime.now(TZ).date(), format="DD/MM/YYYY", key="agenda_filter_date")
        status = status_col.selectbox("Situação", ["Todos", *STATUS_OPTIONS.keys()], key="agenda_filter_status")
        day_only = st.checkbox("Mostrar somente este dia", value=False, key="agenda_day_only")
        filtered = appointment_df.copy()
        if day_only:
            filtered = filtered[filtered["data_local"] == day]
        if status != "Todos":
            filtered = filtered[filtered["status"] == STATUS_OPTIONS[status]]
        filtered = filtered.sort_values(["data_local", "Horário"])
        visible_cols = ["Data", "Horário", "cliente", "serviço", "profissional", "status_nome", "valor", "notes"]
        st.dataframe(filtered[visible_cols], use_container_width=True, hide_index=True)

    st.markdown("### Atualizar status")
    appointment_options = {
        f"#{int(row['id'])} · {row.get('cliente', 'Cliente')} · {row.get('serviço', 'Serviço')} · {row.get('scheduled_at', '')}": int(row["id"])
        for _, row in appointment_df.iterrows()
    }

    with st.container(border=True):
        c1, c2 = st.columns([0.7, 0.3])
        selected_appointment = c1.selectbox("Agendamento", list(appointment_options.keys()))
        selected_status = c2.selectbox("Novo status", list(STATUS_OPTIONS.keys()))

        if st.button("Atualizar status do agendamento"):
            appointment_id = appointment_options[selected_appointment]
            try:
                api_patch(f"/appointments/{appointment_id}/status", json={"status": STATUS_OPTIONS[selected_status]})
            except BeautyFlowAPIError as exc:
                st.error(str(exc))
            else:
                st.success("Status atualizado com sucesso.")
                st.rerun()

    st.markdown("### Reagendar")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        selected_reschedule = c1.selectbox(
            "Agendamento para reagendar",
            list(appointment_options.keys()),
            key="reschedule_appointment",
        )
        new_date = c2.date_input(
            "Nova data",
            value=datetime.now(TZ).date() + timedelta(days=1),
            key="reschedule_date",
        )
        new_time = c3.time_input("Novo horário", value=time(14, 0), key="reschedule_time")

        if st.button("Confirmar reagendamento"):
            appointment_id = appointment_options[selected_reschedule]
            try:
                api_patch(
                    f"/appointments/{appointment_id}/reschedule",
                    json={"scheduled_at": datetime.combine(new_date, new_time).isoformat()},
                )
            except BeautyFlowAPIError as exc:
                st.error(str(exc))
            else:
                st.success("Agendamento reagendado com sucesso.")
                st.rerun()
