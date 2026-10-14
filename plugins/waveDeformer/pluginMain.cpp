#include "waveDeformer.h"

#include <maya/MFnPlugin.h>
#include <maya/MGlobal.h>

namespace
{
const char* const kVersion = "0.1.0";
}

MStatus initializePlugin(MObject obj)
{
    MFnPlugin plugin(obj, "Chuiko Mykhail", kVersion, "Any");

    MStatus status = plugin.registerNode(WaveDeformer::typeName, WaveDeformer::id, WaveDeformer::creator,
                                         WaveDeformer::initialize, MPxNode::kDeformerNode);
    if (!status)
    {
        // CHECK_MSTATUS output goes to the Output Window; this reaches the Script Editor / maya_log.
        MGlobal::displayError(MString("waveDeformer: registerNode failed: ") + status.errorString());
        return status;
    }

    MGlobal::displayInfo(MString("waveDeformer ") + kVersion + " loaded (built " __DATE__ " " __TIME__ ")");
    return MS::kSuccess;
}

MStatus uninitializePlugin(MObject obj)
{
    MFnPlugin plugin(obj);

    MStatus status = plugin.deregisterNode(WaveDeformer::id);
    if (!status)
    {
        MGlobal::displayError(MString("waveDeformer: deregisterNode failed: ") + status.errorString());
        return status;
    }

    MGlobal::displayInfo("waveDeformer unloaded");
    return MS::kSuccess;
}
