"""Numeric check of the waveDeformer plugin, run inside Maya (e.g. through MCP maya-dev execute_python):

    import runpy
    t = runpy.run_path(r"D:/Claude/Maya MCP test/plugins/waveDeformer/tests/test_waveDeformer.py")
    t["run"]()                  # creates test_wave*, checks, deletes them
    t["run"](keep=True)         # keep the objects for viewport_capture, then t["cleanup"]()

Every vertex of a 10x2 plane (41 points along X) is compared with
    y = envelope * amplitude * sin(2*pi*x / wavelength + phase)
for several attribute sets; AssertionError on any mismatch.
"""
import math

import maya.api.OpenMaya as om
import maya.cmds as cmds

PLANE = "test_wavePlane"
DEFORMER = "test_waveDeformer"
TOLERANCE = 1e-5  # mesh points are stored as floats

# (amplitude, wavelength, phase, envelope); the last one stays applied for a visual check.
CASES = [
    (1.25, 2.5, 0.7, 1.0),
    (1.0, 4.0, 0.0, 0.5),
    (1.0, 4.0, 0.0, 0.0),
    (0.5, 4.0, 0.0, 1.0),
]


def cleanup():
    for node in (DEFORMER, PLANE):
        if cmds.objExists(node):
            cmds.delete(node)
    leftovers = cmds.ls("test_wave*")
    if leftovers:
        cmds.delete(leftovers)


def _points(node):
    sel = om.MSelectionList()
    sel.add(node)
    mesh = om.MFnMesh(sel.getDagPath(0).extendToShape())
    return [(p.x, p.y, p.z) for p in mesh.getPoints(om.MSpace.kObject)]


def _expected(rest, amplitude, wavelength, phase, envelope):
    k = 2.0 * math.pi / wavelength
    return [(x, y + envelope * amplitude * math.sin(k * x + phase), z) for x, y, z in rest]


def run(keep=False):
    if "waveDeformer" not in (cmds.pluginInfo(query=True, listPlugins=True) or []):
        raise RuntimeError("waveDeformer plugin is not loaded")

    cleanup()
    plane = cmds.polyPlane(name=PLANE, width=10, height=2, subdivisionsX=40, subdivisionsY=2,
                           constructionHistory=False)[0]
    rest = _points(plane)
    deformer = cmds.deformer(plane, type="waveDeformer", name=DEFORMER)[0]

    report = {"vertices": len(rest), "cases": []}
    for amplitude, wavelength, phase, envelope in CASES:
        cmds.setAttr(deformer + ".amplitude", amplitude)
        cmds.setAttr(deformer + ".wavelength", wavelength)
        cmds.setAttr(deformer + ".phase", phase)
        cmds.setAttr(deformer + ".envelope", envelope)
        actual = _points(plane)
        expected = _expected(rest, amplitude, wavelength, phase, envelope)
        error = max(abs(a - e) for pa, pe in zip(actual, expected) for a, e in zip(pa, pe))
        report["cases"].append({"amp": amplitude, "wl": wavelength, "phase": phase, "env": envelope,
                                "max_error": error})
        assert error < TOLERANCE, "amp=%s wl=%s phase=%s env=%s: max error %g" % (
            amplitude, wavelength, phase, envelope, error)

    # Last case (A=0.5, wavelength=4): x = -5 + 0.25*i, so i=24 (x=1) is a crest, i=16 (x=-1) a trough,
    # i=20 (x=0) a node. polyPlane numbers the first row along X.
    actual = _points(plane)
    report["samples"] = {i: tuple(round(c, 6) for c in actual[i]) for i in (16, 20, 24)}
    assert abs(actual[24][1] - 0.5) < TOLERANCE and abs(actual[16][1] + 0.5) < TOLERANCE
    assert abs(actual[20][1]) < TOLERANCE

    bbox = cmds.exactWorldBoundingBox(plane)
    report["bbox"] = [round(v, 6) for v in bbox]
    assert abs(bbox[1] + 0.5) < TOLERANCE and abs(bbox[4] - 0.5) < TOLERANCE, bbox
    assert abs(bbox[0] + 5) < TOLERANCE and abs(bbox[3] - 5) < TOLERANCE, bbox

    report["passed"] = True
    if not keep:
        cleanup()
    return report
