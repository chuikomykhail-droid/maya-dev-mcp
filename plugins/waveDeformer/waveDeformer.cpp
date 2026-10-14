#include "waveDeformer.h"

#include <maya/MDataBlock.h>
#include <maya/MFnNumericAttribute.h>
#include <maya/MItGeometry.h>
#include <maya/MPointArray.h>

#include <algorithm>
#include <cmath>

namespace
{
constexpr double kMinWavelength = 0.001;
}

// 0x00000000-0x0007FFFF is Autodesk's range for local/test plugins that are not distributed.
const MTypeId WaveDeformer::id(0x0007F001);
const MString WaveDeformer::typeName("waveDeformer");

MObject WaveDeformer::amplitude;
MObject WaveDeformer::wavelength;
MObject WaveDeformer::phase;

void* WaveDeformer::creator()
{
    return new WaveDeformer();
}

MStatus WaveDeformer::initialize()
{
    MStatus status;
    MFnNumericAttribute nAttr;

    amplitude = nAttr.create("amplitude", "amp", MFnNumericData::kDouble, 1.0, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    nAttr.setKeyable(true);
    nAttr.setSoftMin(0.0);
    nAttr.setSoftMax(5.0);

    // "wl" is taken by the inherited weightList attribute.
    wavelength = nAttr.create("wavelength", "wvl", MFnNumericData::kDouble, 4.0, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    nAttr.setKeyable(true);
    nAttr.setMin(kMinWavelength);
    nAttr.setSoftMax(20.0);

    phase = nAttr.create("phase", "ph", MFnNumericData::kDouble, 0.0, &status);
    CHECK_MSTATUS_AND_RETURN_IT(status);
    nAttr.setKeyable(true);
    nAttr.setSoftMin(0.0);
    nAttr.setSoftMax(2.0 * M_PI);

    for (const MObject& attr : {amplitude, wavelength, phase})
    {
        CHECK_MSTATUS_AND_RETURN_IT(addAttribute(attr));
        CHECK_MSTATUS_AND_RETURN_IT(attributeAffects(attr, outputGeom));
    }
    return MS::kSuccess;
}

MStatus WaveDeformer::deform(MDataBlock& block, MItGeometry& iter, const MMatrix& /*localToWorld*/,
                             unsigned int multiIndex)
{
    MStatus status;
    const float env = block.inputValue(envelope, &status).asFloat();
    CHECK_MSTATUS_AND_RETURN_IT(status);
    const double amp = block.inputValue(amplitude).asDouble();
    const double len = std::max(block.inputValue(wavelength).asDouble(), kMinWavelength);
    const double ph = block.inputValue(phase).asDouble();

    if (env == 0.0f || amp == 0.0)
        return MS::kSuccess;

    const double k = 2.0 * M_PI / len;

    // allPositions() returns points in iteration order, so n follows iter while
    // iter.index() is the component index used for the paintable weights.
    MPointArray points;
    CHECK_MSTATUS_AND_RETURN_IT(iter.allPositions(points));
    unsigned int n = 0;
    for (iter.reset(); !iter.isDone(); iter.next(), ++n)
    {
        const float weight = weightValue(block, multiIndex, iter.index());
        MPoint& p = points[n];
        p.y += env * weight * amp * std::sin(k * p.x + ph);
    }
    return iter.setAllPositions(points);
}
