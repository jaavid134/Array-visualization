import sys
import os
import numpy as np

from stl import mesh
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QPoint
from OpenGL.GL import *
from OpenGL.GLU import *


class MultiSTLViewer(QOpenGLWidget):
    def __init__(self, folder):
        super().__init__()
        self.folder = folder
        self.meshes = []
        self.colors = []

        # camera / interaction state
        self.rot_x = 25.0
        self.rot_y = -40.0
        self.distance = 500.0
        self.last_pos = QPoint()

        self.load_folder(folder)
        self.center_scene()

    # ------------------------------------------------------
    # Load all STL files from folder
    # ------------------------------------------------------
    def load_folder(self, folder):
        for fname in os.listdir(folder):
            if not fname.lower().endswith(".stl"):
                continue
            path = os.path.join(folder, fname)
            try:
                print("Loading:", fname)
                m = mesh.Mesh.from_file(path)
                self.meshes.append(m)

                # random-ish but bright color for each part
                c = np.random.uniform(0.3, 0.9, size=3)
                self.colors.append(c)
            except Exception as e:
                print("Failed to load", fname, "->", e)

    # ------------------------------------------------------
    # Compute bounding box and camera distance
    # ------------------------------------------------------
    def center_scene(self):
        all_points = []
        for m in self.meshes:
            try:
                pts = m.vectors.reshape(-1, 3)
                all_points.append(pts)
            except Exception:
                continue

        if not all_points:
            # fallback if no geometry
            self.center = np.array([0.0, 0.0, 0.0])
            self.size = 100.0
            self.distance = 500.0
            return

        all_points = np.vstack(all_points)

        # Remove NaN / inf
        all_points = all_points[np.isfinite(all_points).all(axis=1)]

        self.min_xyz = all_points.min(axis=0)
        self.max_xyz = all_points.max(axis=0)
        self.center = (self.min_xyz + self.max_xyz) / 2.0
        diag = self.max_xyz - self.min_xyz
        self.size = float(np.linalg.norm(diag))

        if self.size < 1e-6:
            self.size = 100.0

        # camera distance: a bit farther than diagonal size
        self.distance = max(self.size * 2.5, 200.0)
        print("Scene center:", self.center)
        print("Scene size:", self.size, "distance:", self.distance)

    # ------------------------------------------------------
    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glClearColor(0.12, 0.12, 0.12, 1.0)

        # Slight smoothing
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_POINT_SMOOTH)

    # ------------------------------------------------------
    def resizeGL(self, w, h):
        glViewport(0, 0, w, h if h > 0 else 1)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w / float(h if h > 0 else 1), 0.1, 100000.0)
        glMatrixMode(GL_MODELVIEW)

    # ------------------------------------------------------
    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # camera at (0,0,+distance), looking at origin
        gluLookAt(0.0, 0.0, self.distance,
                  0.0, 0.0, 0.0,
                  0.0, 1.0, 0.0)

        # apply rotations from mouse
        glRotatef(self.rot_x, 1.0, 0.0, 0.0)
        glRotatef(self.rot_y, 0.0, 1.0, 0.0)

        # move scene so its center is at origin
        glTranslatef(-self.center[0], -self.center[1], -self.center[2])

        # draw stuff
        self.draw_axes()
        #self.draw_bbox()
        self.draw_meshes()

    # ------------------------------------------------------
    def draw_meshes(self):
        for m, color in zip(self.meshes, self.colors):
            glColor3f(*color)
            glBegin(GL_TRIANGLES)
            for tri in m.vectors:
                # you can compute normals if needed; here we just draw
                for v in tri:
                    glVertex3f(v[0], v[1], v[2])
            glEnd()

    # ------------------------------------------------------
    def draw_axes(self, length=200.0):
        glLineWidth(2.0)
        glBegin(GL_LINES)
        # X — red
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(length, 0, 0)
        # Y — green
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, length, 0)
        # Z — blue
        glColor3f(0.0, 0.6, 1.0)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, length)
        glEnd()

    # ------------------------------------------------------
    '''
    def draw_bbox(self):
        glColor3f(1.0, 1.0, 1.0)
        glLineWidth(1.0)
        x0, y0, z0 = self.min_xyz
        x1, y1, z1 = self.max_xyz

        glBegin(GL_LINES)
        # bottom rectangle
        glVertex3f(x0, y0, z0); glVertex3f(x1, y0, z0)
        glVertex3f(x1, y0, z0); glVertex3f(x1, y1, z0)
        glVertex3f(x1, y1, z0); glVertex3f(x0, y1, z0)
        glVertex3f(x0, y1, z0); glVertex3f(x0, y0, z0)
        # top rectangle
        glVertex3f(x0, y0, z1); glVertex3f(x1, y0, z1)
        glVertex3f(x1, y0, z1); glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z1); glVertex3f(x0, y1, z1)
        glVertex3f(x0, y1, z1); glVertex3f(x0, y0, z1)
        # vertical edges
        glVertex3f(x0, y0, z0); glVertex3f(x0, y0, z1)
        glVertex3f(x1, y0, z0); glVertex3f(x1, y0, z1)
        glVertex3f(x1, y1, z0); glVertex3f(x1, y1, z1)
        glVertex3f(x0, y1, z0); glVertex3f(x0, y1, z1)
        glEnd()
    '''
    # ------------------------------------------------------
    # Mouse interaction
    # ------------------------------------------------------
    def mousePressEvent(self, event):
        self.last_pos = event.position().toPoint()

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        dx = pos.x() - self.last_pos.x()
        dy = pos.y() - self.last_pos.y()

        if event.buttons() & Qt.LeftButton:
            self.rot_x += dy * 0.4
            self.rot_y += dx * 0.4

        self.last_pos = pos
        self.update()

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        # zoom: scroll up -> closer, down -> farther
        factor = 1.0 - delta * 0.001
        factor = max(0.1, min(5.0, factor))
        self.distance *= factor
        self.distance = max(10.0, min(self.distance, 100000.0))
        self.update()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("3D STL Viewer (Array + Canopy)")

        # if script is in the same folder as the STLs, use "."
        stl_folder = "."
        viewer = MultiSTLViewer(stl_folder)
        self.setCentralWidget(viewer)


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.resize(900, 700)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
