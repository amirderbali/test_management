/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class TestDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        
        this.state = useState({
            // Initialisation calquée sur la structure de ton dictionnaire Python
            test_cases: { total: 0, draft: 0, approved: 0, in_progress: 0, done: 0 },
            test_runs: { total: 0, pass: 0, fail: 0, blocked: 0, running: 0, pass_rate: 0 },
            bugs: { total: 0, new: 0, in_progress: 0, resolved: 0, high: 0, medium: 0, low: 0 },
            top_projects: [],
            runs_by_day: [],
            projects: [],
            tasks: [],
            selectedProject: "",
            selectedTask: "",
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });
    }

    async loadDashboardData() {
        try {
            const data = await this.orm.call(
                "test.dashboard",
                "get_dashboard_data",
                [],
                {
                    project_id: this.state.selectedProject || null,
                    task_id: this.state.selectedTask || null,
                }
            );
            
            if (data) {
                this.state.test_cases = data.test_cases;
                this.state.test_runs = data.test_runs;
                this.state.bugs = data.bugs;
                this.state.top_projects = data.top_projects;
                this.state.runs_by_day = data.runs_by_day;
                this.state.projects = data.projects;
                this.state.tasks = data.tasks;
            }
        } catch (error) {
            console.error("Erreur lors du chargement des données du dashboard QA:", error);
        }
    }

    async onProjectChange(ev) {
        this.state.selectedProject = ev.target.value;
        this.state.selectedTask = ""; 
        await this.loadDashboardData();
    }

    async onTaskChange(ev) {
        this.state.selectedTask = ev.target.value;
        await this.loadDashboardData();
    }
}

TestDashboard.template = "test_management_dashboard_template";
registry.category("actions").add("test_management_dashboard", TestDashboard);