#!/usr/bin/env python3

def main():
    """
    1. read config file to knows the  images:tag and registry and if we need convert to nydus image or not
    2. convert image if we need
    3. collet metrics from nydus image(close prefetch)
    4. analysis the metrics to create the prefetch file list 
    5. use the prefetch file list to rebuild the image
    6. bench the oci image use overlayfs,the nydus image without prefetch and the nydus image with prefetch(maybe we need to enable prefetch by change the config.json and restart the snapshotter service)
    """
    print("test")


if __name__ == "__main__":
    main()