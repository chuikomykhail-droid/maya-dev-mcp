#pragma once

#include <maya/MPxDeformerNode.h>
#include <maya/MString.h>
#include <maya/MTypeId.h>

// Sine wave along the object-space X axis, displacing points in Y:
//   y += envelope * weight * amplitude * sin(2*pi * x / wavelength + phase)
class WaveDeformer : public MPxDeformerNode
{
public:
    static void* creator();
    static MStatus initialize();

    MStatus deform(MDataBlock& block, MItGeometry& iter, const MMatrix& localToWorld,
                   unsigned int multiIndex) override;

    static const MTypeId id;
    static const MString typeName;

    static MObject amplitude;
    static MObject wavelength;
    static MObject phase;
};
