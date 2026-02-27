cmake_minimum_required(VERSION 3.18.0)
project(ben_description)

find_package(ament_cmake REQUIRED)
find_package(xacro REQUIRED)

install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
install(DIRECTORY models DESTINATION share/${PROJECT_NAME})
install(DIRECTORY urdf DESTINATION share/${PROJECT_NAME})

file (ARCHIVE_EXTRACT
  INPUT ${PROJECT_SOURCE_DIR}/models/meshes/BEN_shell.tar.bz2
  DESTINATION share/${PROJECT_NAME}/models/meshes/
)

install(DIRECTORY ${CMAKE_BINARY_DIR}/share/${PROJECT_NAME}/models DESTINATION share/${PROJECT_NAME})


ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh")

ament_export_dependencies(
  xacro
)

ament_package()