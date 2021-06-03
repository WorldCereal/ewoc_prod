#EWoC work plan generation 
The aim of this tool is to prepare and organize the satellite products that will be processed by the EWoC system.
The generated json plan is the starting point for the Argo workflows.

## The anatomy of a plan
A plan is a json file with a list of S2 MGRS tiles and the corresponding satellite products to process.
```json
{
  "31UFS": {
    "SAR_PROC": {
      "INPUTS": [
        "S1A_IW_GRDH_1SDV_20201230T054238_20201230T054303_035911_0434B3_96C7",
        "S1B_IW_GRDH_1SDV_20201229T055005_20201229T055030_024913_02F6E8_1262",
        "S1A_IW_GRDH_1SDV_20201228T055903_20201228T055928_035882_0433B6_B991"
      ]
    },
    "S2_PROC": {
      "INPUTS": [
        {
          "id": "S2A_MSIL1C_20201226T105451_N0209_R051_T31UFS_20201226T130209"
        },
        {
          "id": "S2B_MSIL1C_20201218T104349_N0209_R008_T31UFS_20201218T115054"
        },
        {
          "id": "S2A_MSIL1C_20201213T104441_N0209_R008_T31UFS_20201213T125210"
        },
        {
          "id": "S2B_MSIL1C_20201208T104429_N0209_R008_T31UFS_20201208T114513"
        }
      ]
    },
    "L8_PROC": {
      "INPUTS": []
    },
    "L8_TIRS": [
      "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2020/199/025/LC08_L2SP_199025_20201229_20210310_02_T1/LC08_L2SP_199025_20201229_20210310_02_T1_ST_B10.TIF",
      "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2020/196/025/LC08_L2SP_196025_20201208_20210313_02_T1/LC08_L2SP_196025_20201208_20210313_02_T1_ST_B10.TIF",
      "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2020/198/025/LC08_L2SP_198025_20201206_20210313_02_T1/LC08_L2SP_198025_20201206_20210313_02_T1_ST_B10.TIF",
      "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2020/197/024/LC08_L2SP_197024_20201129_20210316_02_T1/LC08_L2SP_197024_20201129_20210316_02_T1_ST_B10.TIF",
      "s3://usgs-landsat/collection02/level-2/standard/oli-tirs/2020/198/025/LC08_L2SP_198025_20201120_20210315_02_T1/LC08_L2SP_198025_20201120_20210315_02_T1_ST_B10.TIF"
    ]
  }
}
```
In its current version the plan contains 4 sections: SAR_PROC, S2_PROC, L8_PROC and L8_TIRS. The example above is a plan for 31UFS, note that in this case we don't need Landsat-8 level 1 data

## How to generate a plan 
