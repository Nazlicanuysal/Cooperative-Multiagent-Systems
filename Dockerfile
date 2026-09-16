# Temel imaj olarak ROS 2 Humble (veya kullandığın sürüm) masaüstü versiyonunu alıyoruz
FROM osrf/ros:humble-desktop

# Gazebo, Nav2, SLAM ve diğer gerekli sistem paketlerini kuruyoruz
RUN apt-get update && apt-get install -y \
    ros-humble-gazebo-ros-pkgs \
    ros-humble-navigation2 \
    ros-humble-nav2-bringup \
    ros-humble-slam-toolbox \
    ros-humble-xacro \
    ros-humble-robot-state-publisher \
    python3-pip \
    python3-colcon-common-extensions \
    sqlite3 \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Container içinde bir çalışma alanı oluştur
WORKDIR /ros2_ws

# Senin bilgisayarındaki 'src' (rob_one vb. paketlerin olduğu) klasörünü container'a kopyala
COPY src/ /ros2_ws/src/

# ROS 2 ortamını aktif et ve projeyi derle
RUN /bin/bash -c "source /opt/ros/humble/setup.bash && \
    colcon build --symlink-install"

# Container her açıldığında ROS 2 ve senin projeni otomatik tanısın
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc
RUN echo "source /ros2_ws/install/setup.bash" >> ~/.bashrc

CMD ["/bin/bash"]


