import dna_nanotube_tools
from PyQt6.QtWidgets import QApplication
import pyqtgraph as pg
import sys

interior_angle_multiples = [4]

def visualize_widget(widget):
    app = QApplication(sys.argv)
    widget.show()
    app.exec()

base_angle = 2 * (360 / 21)
side_view = dna_nanotube_tools.plot.side_view(
    interior_angle_multiples, 3.38, base_angle, 12.6, 0
)

base_count = 36
xs_NEMid = side_view.xs(base_count, NEMid=True)[0]
zs_NEMid = side_view.zs(base_count, NEMid=True)[0]

win = pg.GraphicsLayoutWidget()
win.setWindowTitle("Side View of DNA")
main_plot = win.addPlot()

for strand_direction, color in enumerate(["b", "g"]):
    print(strand_direction, [round(NEMid, 3) for NEMid in xs_NEMid[strand_direction]])
    print(strand_direction, [round(NEMid, 3) for NEMid in zs_NEMid[strand_direction]])

    main_plot.plot(
        xs_NEMid[strand_direction],
        zs_NEMid[strand_direction],
        title="Up Strand",
        symbol="x",
        symbolSize=12,
        pxMode=True,
        symbolPen=color,
    )

app = QApplication(sys.argv)
# win.setAspectLocked(lock=True, ratio=1)
# win.showGrid(x=True, y=True)
win.show()
app.exec()