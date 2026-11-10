
# Queen's Intelligent Robotic Companion (QIRC)
Mren 403: Capstone\
Authors: Lukas Hendry, Pablo Silva, Liam McIntaggart, Vikram Lew
# Overview
The QIRC is a mobile robot capable of storing, dispensing, and delivering pill medication to the customer <expand>

# Github structure
## Software Architecture
![](softwareArchitectureV2.png)
The QIRC uses ros2 (vers:tbd) to communicated within nodes.

## Perception Package
THe package focuses on usinsg camera input from the realsense camera d### and the \<surge camera\> to detect objects, persons and stairwell.
### Camera Node
Primary node responsible for 

## Localization Package
Uses Lidar input 
### Localziation Node
Uses map to find out where we are. 
### Mapping node
Make map

## Planning Package
Decides where vehicle goes
### Vehicle manager node
Operates everything. 
### Global Planner node
Uses G* star algorithm to plan
### Local planner node
Avoids obstacles

## Control Package
COntrols the vehicle
### Control Node
MPC algorithm

## Pill Dispenser Package
### Pill box Node
Controls how much pills are dispense
### Arm Node
lifts the arm when approproaite