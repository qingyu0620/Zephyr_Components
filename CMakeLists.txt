cmake_minimum_required(VERSION 3.20.0)
set(BOARD ek_ra2l1)
set(BOARD_FLASH_RUNNER pyocd)
set(BOARD_DEBUG_RUNNER pyocd)
set(BOARD_RUNNER_ARGS_pyocd "--frequency=1000000")
# 如需使用 JLink, 将上面两行的 pyocd 改为 jlink
# 如需使用 DAP-Link (OpenOCD), 改为 openocd 并添加:
# set(BOARD_RUNNER_ARGS_openocd "--config=${CMAKE_CURRENT_SOURCE_DIR}/config/openocd_dap.cfg")
find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE})
project(blinky)

# 源文件目录列表（在此添加新的源文件目录，会自动递归搜索 .c 文件）
set(APP_SOURCE_DIRS
    apps
    communication
    controller
    src
    thread
    # src/xxx
)

# 头文件目录列表（在此添加新的头文件目录，会自动递归搜索子目录）
set(APP_INCLUDE_DIRS
    apps
    communication
    controller
    src
    thread
    topic
    include
    # src/xxx
)

foreach(dir ${APP_SOURCE_DIRS})
    file(GLOB_RECURSE DIR_SOURCES ${dir}/*.c ${dir}/*.cpp)
    list(APPEND APP_SOURCES ${DIR_SOURCES})
endforeach()

target_sources(app PRIVATE ${APP_SOURCES})
target_include_directories(app PRIVATE ${APP_INCLUDE_DIRS})

# bsp/ 和 modules/ 通过 mod_init.py 从 Zephyr_Components 仓库拉取
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/bsp)
  add_subdirectory(bsp)
endif()
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/modules)
  add_subdirectory(modules)
endif()
if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/EmbedKit)
  add_subdirectory(EmbedKit)
  target_link_libraries(app PRIVATE embedkit)
endif()

# 按实际拉取的模块链接
if(TARGET mod_led)
  target_link_libraries(app PRIVATE mod_led)
endif()
if(TARGET mod_key)
  target_link_libraries(app PRIVATE mod_key)
endif()












