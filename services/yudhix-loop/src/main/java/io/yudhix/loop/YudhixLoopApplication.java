package io.yudhix.loop;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"io.yudhix.loop", "io.yudhix.common"})
public class YudhixLoopApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudhixLoopApplication.class, args);
    }
}
