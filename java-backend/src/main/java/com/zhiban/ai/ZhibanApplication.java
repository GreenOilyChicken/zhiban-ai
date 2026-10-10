package com.zhiban.ai;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 知伴AI双端智能体APP - 后端启动类
 *
 * @author zhiban
 */
@SpringBootApplication
@MapperScan("com.zhiban.ai.mapper")
public class ZhibanApplication {

    public static void main(String[] args) {
        SpringApplication.run(ZhibanApplication.class, args);
    }
}
