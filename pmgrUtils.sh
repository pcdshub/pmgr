#! /bin/bash

# Set up env
export PSPKG_ROOT=/reg/g/pcds/pkg_mgr
export PSPKG_RELEASE=controls-0.1.0
source $PSPKG_ROOT/etc/set_env.sh

# Check if this is amo or sxr
if [[ "${2:0:3}" == "SXR" ]] || [[ "${2:0:3}" == "AMO" ]]; then
    sxd=true
else
    sxd=false
fi

# Check if this is a hard x-ray hutch
if [[ "${2:0:3}" == "XPP" ]] || [[ "${2:0:3}" == "XCS" ]] || 
[[ "${2:0:3}" == "MFX" ]] || [[ "${2:0:3}" == "CXI" ]] || [[ "${2:0:3}" == "MEC" ]]; then
    hxr=true
else
    hxr=false
fi

# Check for hutch-specific options
dir=`dirname $(readlink -f "$0")`
if [[ "$1" == "apply" ]] && [ "$sxd" = true ] ; then
    python $dir/pmgrUtils.py $@ --hutch=sxd
elif [ "$hxr" = true ] ; then
    python $dir/pmgrUtils.py $@
else
    python $dir/pmgrUtils.py $@
fi
