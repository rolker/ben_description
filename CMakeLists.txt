cmake_minimum_required(VERSION 3.18.0)
project(ben_description)

find_package(ament_cmake REQUIRED)
find_package(xacro REQUIRED)

install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
install(DIRECTORY models DESTINATION share/${PROJECT_NAME})
install(DIRECTORY rviz DESTINATION share/${PROJECT_NAME})
install(DIRECTORY urdf DESTINATION share/${PROJECT_NAME})

file (ARCHIVE_EXTRACT
  INPUT ${PROJECT_SOURCE_DIR}/models/meshes/BEN_shell.tar.bz2
  DESTINATION share/${PROJECT_NAME}/models/meshes/
)

# BEN_shell_collision.stl is small enough to install directly (no archive needed)

install(DIRECTORY ${CMAKE_BINARY_DIR}/share/${PROJECT_NAME}/models DESTINATION share/${PROJECT_NAME})


ament_environment_hooks("hooks/resource_paths.dsv.in")
ament_environment_hooks("hooks/resource_paths.sh")

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  # The test reads the installed files, so it runs after colcon build.
  ament_add_pytest_test(test_description test/test_description.py
    ENV BEN_DESCRIPTION_INSTALL_PREFIX=${CMAKE_INSTALL_PREFIX}
    TIMEOUT 60
  )
endif()

ament_export_dependencies(
  xacro
)

ament_package()