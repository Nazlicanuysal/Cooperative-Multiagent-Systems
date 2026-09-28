Dockerized ROS 2 & STM32 hybrid architecture for a Cooperative Multi-Agent Autonomous Mobile Robot (AMR) fleet. Kocaeli University Mechatronics Engineering Senior Design Project.



Cooperative Hybrid Multi-Agent AMR Fleet Management
This repository contains the Dockerized simulation and control environment for our Mechatronics Engineering Senior Design Project. It provides an isolated, cross-platform (Windows/Linux) workspace to deploy a scalable Autonomous Mobile Robot (AMR) fleet.

Key Features:

    Hybrid Architecture: High-level ROS 2 autonomy (Nav2, Gazebo, SLAM) bridging with low-level STM32 real-time control.

    Task Allocation: Consensus-Based Auction Algorithm (CBAA) for decentralized agent negotiation.

    Centralized Logging: SQLite-based dispatcher for task announcement and deadlock override.

    Containerized Workflow: Ready-to-run Docker environment eliminating dependency issues.
