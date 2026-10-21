package io.yudhix.ledger;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;

@SpringBootApplication
@ComponentScan(basePackages = {"io.yudhix.ledger", "io.yudhix.common"})
public class YudhixLedgerApplication {

    public static void main(String[] args) {
        SpringApplication.run(YudhixLedgerApplication.class, args);
    }
}
