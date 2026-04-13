/**
 * @file trd_servo.cpp
 * @author qingyu
 * @brief 
 * @version 0.1
 * @date 2026-04-13
 * 
 * @copyright Copyright (c) 2026
 * 
 */

#include "trd_servo.h"
#include "zephyr/kernel.h"

using namespace thread;

static void Task(void* p1, void* p2, void* p3)
{
    auto& ins = *static_cast<Thread<Servo, servo::N>*>(p1);

    for (;;)
    {
        ins[SERVO0].SetPulse(500);
        k_msleep(1000);
        ins[SERVO0].SetPulse(2500);
        k_msleep(1000);
    }
}

void servo::thread_start(uint8_t prio)
{
    servo::thread_.Start(prio, Task);
}
