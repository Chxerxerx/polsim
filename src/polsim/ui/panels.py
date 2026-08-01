"""District information panel (Milestone 2.5)."""

from __future__ import annotations

from PySide6.QtWidgets import QFormLayout, QLabel, QWidget

from polsim.ui.viewmodels import DistrictView


class DistrictInfoPanel(QWidget):
    """Shows the selected district's snapshot values."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QFormLayout(self)
        self._name = QLabel("—")
        self._province = QLabel("—")
        self._population = QLabel("—")
        self._income = QLabel("—")
        self._urban = QLabel("—")
        layout.addRow("District", self._name)
        layout.addRow("Province", self._province)
        layout.addRow("Population", self._population)
        layout.addRow("Mean weekly income", self._income)
        layout.addRow("Urban share", self._urban)

    def show_district(self, view: DistrictView | None) -> None:
        if view is None:
            for label in (self._name, self._province, self._population, self._income, self._urban):
                label.setText("—")
            return
        self._name.setText(view.name)
        self._province.setText(view.province_name)
        self._population.setText(f"{view.population:,}")
        self._income.setText(f"{view.mean_income:,.1f}")
        self._urban.setText(f"{view.urban_share:.1%}")

    def district_text(self) -> str:
        return f"{self._name.text()} | {self._province.text()} | {self._population.text()}"
