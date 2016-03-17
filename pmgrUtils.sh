#! /bin/bash

# Set up env
export PSPKG_ROOT=/reg/common/package
export PSPKG_RELEASE=controls-0.0.8
source $PSPKG_ROOT/etc/set_env.sh
source /reg/g/pcds/setup/pyca27.sh

# Check if this is amo or sxr
if [[ "${2:0:3}" == "SXR" ]] || [[ "${2:0:3}" == "AMO" ]]; then
    sxd=true
else
    sxd=false
fi

# Look for configurations in both the sxr and amo pmgrs if using apply
if [[ "$1" == "apply" ]] && [ "$sxd" = true ] ; then
    python /reg/g/pcds/pyps/apps/pmgr/latest/pmgrUtils.py $1 $2 -v -z --hutch=sxd
else
    python /reg/g/pcds/pyps/apps/pmgr/latest/pmgrUtils.py $1 $2 -v -z
fi
