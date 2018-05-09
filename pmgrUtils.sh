#! /bin/bash

# Set up env
unset PYTHONPATH
unset LD_LIBRARY_PATH
source /reg/g/pcds/pyps/conda/py36/etc/profile.d/conda.sh
VER="pcds-1.0.0"
conda activate "${VER}"

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
