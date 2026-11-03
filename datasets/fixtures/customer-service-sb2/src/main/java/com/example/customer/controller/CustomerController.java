package com.example.customer.controller;

import com.example.customer.model.Customer;
import javax.servlet.http.HttpServletRequest;

public class CustomerController {

    public String handleRequest(HttpServletRequest request) {
        String remoteAddr = request.getRemoteAddr();
        return "Processed request from " + remoteAddr;
    }

    public Customer createCustomer(String name, String email) {
        return new Customer(1L, name, email);
    }
}
