package io.yudhix.radar;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"io.yudhix.radar", "io.yudhix.common"})
public class YudhixRadarApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudhixRadarApplication.class, args);
    }
}
